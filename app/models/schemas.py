from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class Message(BaseModel):
    sender: str = Field(..., description="Either 'scammer' or 'user'")
    text: str = Field(..., description="Message content")
    timestamp: int = Field(..., description="Epoch time in milliseconds")


class Metadata(BaseModel):
    channel: Optional[str] = Field("SMS", description="Communication channel")
    language: Optional[str] = Field("English", description="Language used")
    locale: Optional[str] = Field("IN", description="Country or region")


class HoneypotRequest(BaseModel):
    sessionId: str = Field(..., description="Unique session identifier")
    message: Message = Field(..., description="Latest incoming message")
    conversationHistory: List[Message] = Field(default=[], description="Previous messages")
    metadata: Optional[Metadata] = Field(default=None, description="Additional metadata")


class HoneypotResponse(BaseModel):
    status: str = Field(..., description="Response status")
    reply: str = Field(..., description="AI agent's reply to scammer")


class ExtractedIntelligence(BaseModel):
    bankAccounts: List[str] = Field(default=[], description="Extracted bank account numbers")
    upiIds: List[str] = Field(default=[], description="Extracted UPI IDs")
    phishingLinks: List[str] = Field(default=[], description="Extracted phishing URLs")
    phoneNumbers: List[str] = Field(default=[], description="Extracted phone numbers")
    suspiciousKeywords: List[str] = Field(default=[], description="Detected suspicious keywords")


class FinalResultPayload(BaseModel):
    sessionId: str = Field(..., description="Session ID")
    scamDetected: bool = Field(..., description="Whether scam was confirmed")
    totalMessagesExchanged: int = Field(..., description="Total message count")
    extractedIntelligence: ExtractedIntelligence = Field(..., description="Collected intelligence")
    agentNotes: str = Field(..., description="Summary of scammer behavior")


# Internal session tracking
class SessionData(BaseModel):
    sessionId: str
    conversationHistory: List[Message] = []
    stage: str = "trust"  # trust, extract, stall
    memory: Dict[str, List[str]] = {}
    totalMessages: int = 0
    scamDetected: bool = False
    extractedIntelligence: ExtractedIntelligence = ExtractedIntelligence()
    suspiciousKeywords: List[str] = []
    agentNotes: str = ""
    createdAt: datetime = Field(default_factory=datetime.utcnow)