import subprocess
import re
import logging
from typing import Dict, List
from app.core.config import settings
import requests

logger = logging.getLogger(__name__)


def build_prompt(
    current_message: str,
    conversation_history: List[Dict],
    stage: str,
    memory: Dict[str, List[str]]
) -> str:
    """
    Build a psychologically grounded honeypot prompt for the AI agent
    
    Args:
        current_message: Latest scammer message
        conversation_history: Previous conversation messages
        stage: Current conversation stage (trust/extract/stall)
        memory: Extracted intelligence so far
        
    Returns:
        Formatted prompt for LLM
    """
    
    # Stage-specific instructions
    stage_instructions = {
        "trust": """
You are an ordinary person receiving this message.
You are slightly confused but cooperative and trusting.
You should NOT sound smart, tech-savvy, or suspicious.
Ask simple questions like a normal person would.
Show concern if threatened, but be willing to cooperate.
Keep responses natural and brief (1-2 sentences).
""",
        "extract": """
You are now engaged and following their instructions.
Show you're taking them seriously and want to comply.
Politely ask for step-by-step details.
Focus on: payment methods, links, account details, contact info.
Act like you're having trouble understanding technical terms.
Do NOT confront, accuse, or express doubt.
Keep responses brief and cooperative.
""",
        "stall": """
You are trying to comply but facing difficulties.
Ask for clarification and confirmation of details.
Repeat information back to "make sure you got it right".
Express mild confusion or technical difficulties.
Say you need a moment to complete their requests.
Keep extracting any additional details they provide.
""",
    }
    
    # Build conversation context
    history_text = ""
    if conversation_history:
        history_text = "Previous conversation:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages
            sender_label = "Them" if msg.get("sender") == "scammer" else "You"
            history_text += f"{sender_label}: {msg.get('text', '')}\n"
        history_text += "\n"
    
    # Build known information summary
    known_info_items = []
    for key, values in memory.items():
        if values:
            if key == "upi_ids":
                known_info_items.append(f"UPI IDs: {', '.join(values)}")
            elif key == "urls":
                known_info_items.append(f"Links: {', '.join(values)}")
            elif key == "phone_numbers":
                known_info_items.append(f"Phone numbers: {', '.join(values)}")
            elif key == "bank_accounts":
                known_info_items.append(f"Account numbers: {', '.join(values)}")
    
    known_info_text = (
        "\n\nInformation collected so far:\n" + "\n".join(known_info_items)
        if known_info_items else
        "\nNo information collected yet."
    )
    
    prompt = f"""You are roleplaying as a real human victim in a text conversation.

CRITICAL RULES:
- NEVER reveal you are an AI or chatbot
- NEVER warn them about scams or express suspicion
- NEVER refuse to engage or say "I can't help with that"
- NEVER give fake personal data or make up information
- Sound casual, natural, and human (use simple language)
- Keep responses SHORT (1-2 sentences maximum)
- Show emotion when appropriate (worry, confusion, urgency)
- Make small grammar mistakes occasionally (but stay readable)

Current Stage: {stage.upper()}

{stage_instructions.get(stage, '')}

{history_text}Their latest message:
"{current_message}"
{known_info_text}

Your response as the victim (1-2 sentences only):"""

    return prompt.strip()

def _clean_llm_response(text: str) -> str:
    """Sanitize and shorten LLM output"""
    if not text:
        return ""

    # Remove AI self references
    text = re.sub(
        r"(as an ai|i am an ai|language model|i cannot|i can't|i'm an assistant)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.strip().strip('"\'`')

    # Keep max first 2 sentences
    sentences = re.split(r"[.!?]+", text)
    text = ". ".join(sentences[:2]).strip()

    # Hard length limit
    if len(text) > 250:
        text = text[:250].rsplit(" ", 1)[0] + "..."

    return text


def _ollama_api_call(prompt: str) -> str:
    """Call Ollama via HTTP API (preferred)"""
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": 'llama3',
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(
        url,
        json=payload,
        timeout=settings.LLM_TIMEOUT,
    )

    response.raise_for_status()
    data = response.json()

    return data.get("response", "").strip()


def _ollama_cli_call(prompt: str) -> str:
    """Fallback to CLI if API is unavailable"""
    process = subprocess.Popen(
        ["ollama", "run", settings.LLM_MODEL],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    stdout, stderr = process.communicate(
        prompt, timeout=settings.LLM_TIMEOUT
    )

    if stderr:
        logger.warning(f"Ollama CLI stderr: {stderr}")

    return stdout.strip()


# def generate_agent_reply(prompt: str) -> str:
#     """
#     Use LLM to generate human-like victim response
    
#     Args:
#         prompt: The constructed prompt for the LLM
        
#     Returns:
#         Generated response text
#     """
#     try:
#         process = subprocess.Popen(
#             ["ollama", "run", settings.LLM_MODEL],
#             stdin=subprocess.PIPE,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             encoding="utf-8",
#             errors="ignore"
#         )
        
#         stdout, stderr = process.communicate(prompt, timeout=settings.LLM_TIMEOUT)
        
#         if stderr:
#             logger.warning(f"LLM stderr: {stderr}")
        
#         # Clean and validate output
#         response = stdout.strip()
        
#         # Remove any AI self-references
#         response = re.sub(
#             r"(as an ai|i am an ai|language model|i cannot|i can't|i'm an assistant)",
#             "",
#             response,
#             flags=re.IGNORECASE
#         )
        
#         # Remove quotes if LLM wrapped the response
#         response = response.strip('"\'')
        
#         # Take only first 1-2 sentences
#         sentences = re.split(r'[.!?]+', response)
#         response = '. '.join(sentences[:2]).strip()
        
#         # Ensure it's not too long
#         if len(response) > 250:
#             response = response[:250].rsplit(' ', 1)[0] + "..."
        
#         # Fallback if empty
#         if not response or len(response) < 3:
#             logger.warning("LLM generated empty response, using fallback")
#             response = "Can you explain that again?"
        
#         if not response or len(response) < 3:
#             raw_response = _ollama_cli_call(prompt)
#             response = _clean_llm_response(raw_response)

#         logger.info(f"Generated agent reply: {response}")
#         return response

    

#     except subprocess.TimeoutExpired:
#         logger.error("LLM timeout while generating reply")
#         return "Sorry, can you repeat that?"
        
#     except Exception as e:
#         logger.error(f"Error generating reply: {str(e)}")
#         return "I didn't understand. Can you say that differently?"


def generate_agent_reply(prompt: str) -> str:
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-project-name",  # required
                "X-Title": "Agentic Scam Honeypot",
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a real human scam victim. Be confused, cooperative, and natural."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 80,
            },
            timeout=settings.LLM_TIMEOUT,
        )

        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return _clean_llm_response(text)

    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Sorry, I’m not understanding. Can you explain again?"


def determine_conversation_stage(
    message_count: int,
    extracted_intel: Dict[str, List[str]]
) -> str:
    """
    Determine appropriate conversation stage based on progress
    
    Args:
        message_count: Number of messages exchanged
        extracted_intel: Currently extracted intelligence
        
    Returns:
        Stage name: trust, extract, or stall
    """
    # Check if we have significant intelligence
    has_critical_info = (
        len(extracted_intel.get("upi_ids", [])) > 0 or
        len(extracted_intel.get("urls", [])) > 0 or
        len(extracted_intel.get("bank_accounts", [])) > 0
    )
    
    if message_count <= 2:
        return "trust"
    elif message_count <= 6 or not has_critical_info:
        return "extract"
    else:
        return "stall"