import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from models.schemas import SessionData, Message, ExtractedIntelligence
from core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """In-memory session storage for honeypot conversations"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get existing session or return None"""
        session = self._sessions.get(session_id)
        
        if session:
            # Check if session expired
            age = datetime.utcnow() - session.createdAt
            if age > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES):
                logger.warning(f"Session {session_id} expired, removing")
                self._sessions.pop(session_id, None)
                return None
        
        return session
    
    def create_session(self, session_id: str) -> SessionData:
        """Create new session"""
        session = SessionData(
            sessionId=session_id,
            conversationHistory=[],
            stage="trust",
            memory={},
            totalMessages=0,
            scamDetected=False,
            extractedIntelligence=ExtractedIntelligence(),
            suspiciousKeywords=[],
            agentNotes="",
            createdAt=datetime.utcnow()
        )
        
        self._sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        return session
    
    def get_or_create_session(self, session_id: str) -> SessionData:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)
        return session
    
    def update_session(self, session: SessionData):
        """Update session in storage"""
        self._sessions[session.sessionId] = session
        logger.debug(f"Updated session: {session.sessionId}")
    
    def delete_session(self, session_id: str):
        """Remove session from storage"""
        if session_id in self._sessions:
            self._sessions.pop(session_id)
            logger.info(f"Deleted session: {session_id}")
    
    def add_message(self, session: SessionData, message: Message):
        """Add message to conversation history"""
        session.conversationHistory.append(message)
        session.totalMessages += 1
        self.update_session(session)
    
    def update_intelligence(
        self,
        session: SessionData,
        new_intel: Dict
    ):
        """Update extracted intelligence"""
        # Update UPI IDs
        if new_intel.get("upi_ids"):
            existing_upi = set(session.extractedIntelligence.upiIds)
            existing_upi.update(new_intel["upi_ids"])
            session.extractedIntelligence.upiIds = list(existing_upi)
        
        # Update URLs
        if new_intel.get("urls"):
            existing_urls = set(session.extractedIntelligence.phishingLinks)
            existing_urls.update(new_intel["urls"])
            session.extractedIntelligence.phishingLinks = list(existing_urls)
        
        # Update phone numbers
        if new_intel.get("phone_numbers"):
            existing_phones = set(session.extractedIntelligence.phoneNumbers)
            existing_phones.update(new_intel["phone_numbers"])
            session.extractedIntelligence.phoneNumbers = list(existing_phones)
        
        # Update bank accounts
        if new_intel.get("bank_accounts"):
            existing_accounts = set(session.extractedIntelligence.bankAccounts)
            existing_accounts.update(new_intel["bank_accounts"])
            session.extractedIntelligence.bankAccounts = list(existing_accounts)
        
        self.update_session(session)
    
    def cleanup_old_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            age = current_time - session.createdAt
            if age > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Get total active sessions"""
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()