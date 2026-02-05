import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

from app.models.schemas import HoneypotRequest, HoneypotResponse, Message
from app.core.security import verify_api_key
from app.services.ai_service import predict_scam
from app.services.extractor import extract_entities
from app.services.conversation_engine import (
    build_prompt,
    generate_agent_reply,
    determine_conversation_stage
)
from app.services.session_manager import session_manager
from app.services.callback_service import (
    should_send_callback,
    send_final_result,
    build_agent_notes
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/message", response_model=HoneypotResponse)
async def handle_message(
    request: HoneypotRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Main endpoint to handle incoming scam messages
    
    This endpoint:
    1. Authenticates the request
    2. Detects scam intent
    3. Activates AI agent if scam detected
    4. Generates human-like response
    5. Extracts intelligence
    6. Sends final callback when appropriate
    """
    
    # Authenticate
    await verify_api_key(x_api_key)
    
    session_id = request.sessionId
    current_message = request.message
    
    logger.info(f"Processing message for session: {session_id}")
    logger.debug(f"Message: {current_message.text}")
    
    try:
        # Get or create session
        session = session_manager.get_or_create_session(session_id)
        
        # Add incoming message to history
        session_manager.add_message(session, current_message)
        
        # Detect scam (only on first message or if not already detected)
        if not session.scamDetected:
            # Convert conversation history to dict format for AI service
            history_dicts = [
                {
                    "sender": msg.sender,
                    "text": msg.text,
                    "timestamp": msg.timestamp
                }
                for msg in request.conversationHistory
            ]
            
            detection_result = predict_scam(
                text=current_message.text,
                conversation_history=history_dicts
            )
            
            logger.info(f"Scam detection result: {detection_result}")
            
            if detection_result["is_scam"]:
                session.scamDetected = True
                
                # Store suspicious keywords
                if detection_result.get("details", {}).get("matched_keywords"):
                    session.extractedIntelligence.suspiciousKeywords.extend(
                        detection_result["details"]["matched_keywords"]
                    )
                    # Deduplicate
                    session.extractedIntelligence.suspiciousKeywords = list(set(
                        session.extractedIntelligence.suspiciousKeywords
                    ))
                
                logger.info(f"🚨 Scam detected in session {session_id}")
        
        # If not scam detected, respond politely without engagement
        if not session.scamDetected:
            logger.info(f"No scam detected in session {session_id}, minimal response")
            return HoneypotResponse(
                status="success",
                reply="Thank you for the message."
            )
        
        # Extract intelligence from current message
        extracted = extract_entities(current_message.text)
        logger.info(f"Extracted entities: {extracted}")
        
        # Update session intelligence
        session_manager.update_intelligence(session, extracted)
        
        # Also update memory dict for prompt building
        for key, values in extracted.items():
            if values:
                existing = session.memory.get(key, [])
                session.memory[key] = list(set(existing + values))
        
        # Determine conversation stage
        session.stage = determine_conversation_stage(
            message_count=session.totalMessages,
            extracted_intel=extracted
        )
        
        logger.info(f"Conversation stage: {session.stage}")
        
        # Build prompt for AI agent
        prompt = build_prompt(
            current_message=current_message.text,
            conversation_history=[
                {"sender": m.sender, "text": m.text}
                for m in session.conversationHistory[:-1]  # Exclude current message
            ],
            stage=session.stage,
            memory=session.memory
        )
        
        # Generate agent response
        agent_reply = generate_agent_reply(prompt)
        
        # Add agent reply to conversation history
        agent_message = Message(
            sender="user",
            text=agent_reply,
            timestamp=current_message.timestamp + 1000  # 1 second later
        )
        session_manager.add_message(session, agent_message)
        
        # Extract intelligence from agent reply too (in case scammer info slipped in)
        agent_extracted = extract_entities(agent_reply)
        if any(agent_extracted.values()):
            logger.warning(f"Agent accidentally revealed info: {agent_extracted}")
        
        # Update session
        session_manager.update_session(session)
        
        # Check if we should send final callback
        if should_send_callback(session):
            logger.info(f"Conditions met for final callback on session {session_id}")
            
            # Build agent notes
            session.agentNotes = build_agent_notes(session)
            session_manager.update_session(session)
            
            # Send callback (non-blocking, don't fail request if it fails)
            callback_success = send_final_result(session)
            
            if callback_success:
                logger.info(f"✅ Final callback sent successfully for session {session_id}")
            else:
                logger.error(f"❌ Final callback failed for session {session_id}")
        
        # Check if max turns reached
        if session.totalMessages >= settings.MAX_TURNS:
            logger.info(f"Max turns reached for session {session_id}")
            
            # Send final callback if not already sent and scam detected
            if session.scamDetected and not session.agentNotes:
                session.agentNotes = build_agent_notes(session)
                send_final_result(session)
        
        # Return response
        return HoneypotResponse(
            status="success",
            reply=agent_reply
        )
        
    except Exception as e:
        logger.error(f"Error processing message for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Get session information (for debugging/monitoring)"""
    
    await verify_api_key(x_api_key)
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "sessionId": session.sessionId,
        "scamDetected": session.scamDetected,
        "totalMessages": session.totalMessages,
        "stage": session.stage,
        "extractedIntelligence": session.extractedIntelligence.dict(),
        "conversationLength": len(session.conversationHistory)
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Delete a session (for cleanup)"""
    
    await verify_api_key(x_api_key)
    
    session_manager.delete_session(session_id)
    
    return {"message": f"Session {session_id} deleted"}


@router.get("/stats")
async def get_stats(x_api_key: Optional[str] = Header(None)):
    """Get API statistics"""
    
    await verify_api_key(x_api_key)
    
    return {
        "activeSessions": session_manager.get_session_count(),
        "maxTurns": settings.MAX_TURNS,
        "apiVersion": "1.0.0"
    }