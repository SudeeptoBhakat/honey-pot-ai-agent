import subprocess
import json
import logging
from core.config import settings

logger = logging.getLogger(__name__)


def llm_fraud_classification(text: str) -> dict:
    """
    Use LLM to classify message as scam/legitimate/uncertain
    
    Args:
        text: Message text or conversation context
        
    Returns:
        Dict with label, confidence, and reason
    """
    prompt = f"""You are a financial fraud detection expert analyzing text messages.

Classify the following message as one of:
- Scam (fraudulent attempt to steal money/data)
- Legitimate (genuine communication)
- Uncertain (not enough information)

Consider these scam indicators:
- Urgency tactics ("immediate action required")
- Authority impersonation (bank, police, tax dept)
- Request for sensitive info (OTP, password, CVV, UPI ID)
- Threats (account blocked, legal action)
- Too-good-to-be-true offers (lottery, refund, prize)
- Suspicious links or app installations
- Remote access requests (AnyDesk, TeamViewer)

Message to analyze:
\"\"\"
{text}
\"\"\"

Respond STRICTLY in this JSON format (no other text):
{{
    "label": "Scam|Legitimate|Uncertain",
    "confidence": 0.85,
    "reason": "Brief explanation"
}}
"""
    
    try:
        result = subprocess.run(
            ["ollama", "run", settings.LLM_MODEL],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors='ignore',
            timeout=settings.LLM_TIMEOUT
        )
        
        output = result.stdout.strip()
        logger.debug(f"LLM raw output: {output}")
        
        # Try to parse JSON from output
        # Sometimes LLM adds text before/after JSON
        try:
            # Find JSON in output
            start = output.find('{')
            end = output.rfind('}') + 1
            if start != -1 and end > start:
                json_str = output[start:end]
                parsed = json.loads(json_str)
                
                # Validate required fields
                if "label" in parsed and "confidence" in parsed:
                    return {
                        "label": parsed.get("label", "Uncertain"),
                        "confidence": float(parsed.get("confidence", 0.0)),
                        "reason": parsed.get("reason", "")
                    }
        except json.JSONDecodeError as je:
            logger.warning(f"JSON parse error: {je}")
        
        # Fallback parsing
        return {
            "label": "Uncertain",
            "confidence": 0.0,
            "reason": "LLM output parsing failed"
        }
        
    except subprocess.TimeoutExpired:
        logger.error("LLM timeout")
        return {
            "label": "Uncertain",
            "confidence": 0.0,
            "reason": "LLM timeout"
        }
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        return {
            "label": "Uncertain",
            "confidence": 0.0,
            "reason": f"LLM error: {str(e)}"
        }