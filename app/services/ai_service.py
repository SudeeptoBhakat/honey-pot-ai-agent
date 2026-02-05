import logging
from app.services.llm_service import llm_fraud_classification
from typing import Dict, List

logger = logging.getLogger(__name__)

# Enhanced scam keywords with weights
SCAM_KEYWORDS = {
    # Authentication & Verification
    "otp": 5,
    "one time password": 5,
    "kyc": 4,
    "verify your account": 4,
    "verify immediately": 5,
    "verification required": 4,
    
    # Urgency & Threats
    "urgent": 3,
    "immediately": 3,
    "account blocked": 5,
    "account suspended": 5,
    "account will be blocked": 5,
    "limited time": 3,
    "expires today": 4,
    "last chance": 4,
    
    # Authority Impersonation
    "bank officer": 4,
    "customer care": 3,
    "government official": 4,
    "tax department": 4,
    "police": 4,
    
    # Financial Actions
    "refund": 3,
    "cashback": 2,
    "prize": 3,
    "lottery": 4,
    "won": 2,
    "claim": 2,
    
    # Malicious Actions
    "click the link": 5,
    "install app": 5,
    "anydesk": 5,
    "teamviewer": 5,
    "remote access": 5,
    "screen share": 4,
    "download": 3,
    
    # Payment & Banking
    "upi": 3,
    "bank account": 2,
    "credit card": 2,
    "debit card": 2,
    "cvv": 5,
    "pin": 4,
    "password": 4,
    "net banking": 3,
}


def heuristic_scam_score(text: str) -> Dict:
    """
    Fast keyword-based scam detection
    Returns score and matched keywords
    """
    score = 0
    matched_keywords = []
    
    lower_text = text.lower()
    
    for keyword, weight in SCAM_KEYWORDS.items():
        if keyword in lower_text:
            score += weight
            matched_keywords.append(keyword)
    
    return {
        "score": score,
        "matched_keywords": matched_keywords
    }


def predict_scam(text: str, conversation_history: List[Dict] = None) -> Dict:
    """
    Multi-layer scam detection:
    1. Heuristic keyword matching (fast)
    2. LLM-based classification (accurate)
    
    Args:
        text: The message text to analyze
        conversation_history: Optional previous messages for context
        
    Returns:
        Dict with is_scam, confidence, method, and details
    """
    result = {
        "is_scam": False,
        "confidence": 0.0,
        "method": "",
        "details": {}
    }
    
    # Build full context if history available
    full_context = text
    if conversation_history:
        history_text = "\n".join([
            f"{msg.get('sender', 'unknown')}: {msg.get('text', '')}"
            for msg in conversation_history[-5:]  # Last 5 messages for context
        ])
        full_context = f"{history_text}\nCurrent: {text}"
    
    # 1️⃣ Heuristic check (FAST)
    heuristic = heuristic_scam_score(text)
    logger.info(f"Heuristic score: {heuristic['score']}, matched: {heuristic['matched_keywords']}")
    
    if heuristic["score"] >= 6:
        result.update({
            "is_scam": True,
            "confidence": min(heuristic["score"] / 15, 0.95),  # Cap at 0.95
            "method": "heuristic",
            "details": heuristic
        })
        logger.info(f"Scam detected via heuristics: {heuristic['matched_keywords']}")
        return result
    
    # 2️⃣ LLM classification for borderline cases
    try:
        llm_result = llm_fraud_classification(full_context)
        logger.info(f"LLM classification: {llm_result}")
        
        if llm_result["label"].lower() == "scam" and llm_result["confidence"] >= 0.75:
            result.update({
                "is_scam": True,
                "confidence": llm_result["confidence"],
                "method": "llm",
                "details": {
                    "llm_result": llm_result,
                    "heuristic": heuristic
                }
            })
            logger.info(f"Scam detected via LLM: {llm_result['reason']}")
            return result
            
    except Exception as e:
        logger.error(f"LLM classification failed: {str(e)}")
    
    # 3️⃣ If heuristic found some keywords but below threshold
    if heuristic["score"] > 0:
        result.update({
            "is_scam": False,
            "confidence": heuristic["score"] / 15,
            "method": "heuristic_low",
            "details": heuristic
        })
        logger.info(f"Low confidence scam indicators: {heuristic['matched_keywords']}")
    else:
        result["method"] = "none"
        logger.info("No scam indicators detected")
    
    return result