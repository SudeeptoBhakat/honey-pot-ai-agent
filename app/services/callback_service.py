import requests
import logging
from models.schemas import FinalResultPayload, SessionData
from app.core.config import settings

logger = logging.getLogger(__name__)


def should_send_callback(session: SessionData) -> bool:
    """
    Determine if we should send final callback
    
    Criteria:
    - Scam detected
    - At least 3 messages exchanged
    - Has extracted some intelligence OR reached max turns
    """
    has_intelligence = (
        len(session.extractedIntelligence.upiIds) > 0 or
        len(session.extractedIntelligence.phishingLinks) > 0 or
        len(session.extractedIntelligence.phoneNumbers) > 0 or
        len(session.extractedIntelligence.bankAccounts) > 0 or
        len(session.extractedIntelligence.suspiciousKeywords) > 0
    )
    
    reached_max_turns = session.totalMessages >= settings.MAX_TURNS
    
    return (
        session.scamDetected and
        session.totalMessages >= 3 and
        (has_intelligence or reached_max_turns)
    )


def send_final_result(session: SessionData) -> bool:
    """
    Send final intelligence report to GUVI evaluation endpoint
    
    Args:
        session: SessionData with conversation details
        
    Returns:
        True if successful, False otherwise
    """
    
    # Prepare payload
    payload = FinalResultPayload(
        sessionId=session.sessionId,
        scamDetected=session.scamDetected,
        totalMessagesExchanged=session.totalMessages,
        extractedIntelligence=session.extractedIntelligence,
        agentNotes=session.agentNotes or "Conversation completed"
    )
    
    try:
        logger.info(f"Sending final result for session {session.sessionId}")
        logger.debug(f"Payload: {payload.dict()}")
        
        response = requests.post(
            settings.GUVI_CALLBACK_URL,
            json=payload.dict(),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        response.raise_for_status()
        
        logger.info(
            f"Successfully sent final result for session {session.sessionId}. "
            f"Status: {response.status_code}"
        )
        return True
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending final result for session {session.sessionId}")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Error sending final result for session {session.sessionId}: {str(e)}"
        )
        return False
        
    except Exception as e:
        logger.error(
            f"Unexpected error sending final result for session {session.sessionId}: {str(e)}"
        )
        return False


def build_agent_notes(session: SessionData) -> str:
    """
    Generate summary notes about scammer behavior
    
    Args:
        session: SessionData to analyze
        
    Returns:
        Summary string
    """
    notes = []
    
    # Analyze tactics
    if session.extractedIntelligence.suspiciousKeywords:
        keywords = session.extractedIntelligence.suspiciousKeywords[:5]
        notes.append(f"Used tactics: {', '.join(keywords)}")
    
    # Analyze requests
    requested_items = []
    if session.extractedIntelligence.upiIds:
        requested_items.append(f"UPI IDs ({len(session.extractedIntelligence.upiIds)})")
    if session.extractedIntelligence.phishingLinks:
        requested_items.append(f"malicious links ({len(session.extractedIntelligence.phishingLinks)})")
    if session.extractedIntelligence.bankAccounts:
        requested_items.append(f"bank accounts ({len(session.extractedIntelligence.bankAccounts)})")
    
    if requested_items:
        notes.append(f"Requested: {', '.join(requested_items)}")
    
    # Analyze persistence
    if session.totalMessages > 7:
        notes.append(f"Highly persistent ({session.totalMessages} messages)")
    elif session.totalMessages > 4:
        notes.append("Moderately persistent")
    
    # Combine notes
    if notes:
        return ". ".join(notes) + "."
    else:
        return "Limited engagement, minimal intelligence extracted."