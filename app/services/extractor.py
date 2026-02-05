import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Enhanced regex patterns
UPI_REGEX = r"\b[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}\b"
URL_REGEX = r"https?://[^\s]+"
IFSC_REGEX = r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
PHONE_REGEX = r"\b[6-9]\d{9}\b"
BANK_ACCOUNT_REGEX = r"\b\d{9,18}\b"  # Bank account numbers
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract scammer intelligence from text using regex patterns
    
    Args:
        text: Message text to analyze
        
    Returns:
        Dict containing lists of extracted entities
    """
    if not text:
        return {
            "upi_ids": [],
            "urls": [],
            "ifsc_codes": [],
            "phone_numbers": [],
            "bank_accounts": [],
            "emails": []
        }
    
    # Extract all patterns
    upi_ids = list(set(re.findall(UPI_REGEX, text)))
    urls = list(set(re.findall(URL_REGEX, text)))
    ifsc_codes = list(set(re.findall(IFSC_REGEX, text)))
    phone_numbers = list(set(re.findall(PHONE_REGEX, text)))
    emails = list(set(re.findall(EMAIL_REGEX, text)))
    
    # Extract potential bank account numbers (filter out phone numbers)
    potential_accounts = re.findall(BANK_ACCOUNT_REGEX, text)
    bank_accounts = list(set([
        acc for acc in potential_accounts 
        if len(acc) >= 9 and acc not in phone_numbers
    ]))
    
    extracted = {
        "upi_ids": upi_ids,
        "urls": urls,
        "ifsc_codes": ifsc_codes,
        "phone_numbers": phone_numbers,
        "bank_accounts": bank_accounts,
        "emails": emails
    }
    
    # Log extraction results
    total_extracted = sum(len(v) for v in extracted.values())
    if total_extracted > 0:
        logger.info(f"Extracted {total_extracted} entities: {extracted}")
    
    return extracted


def merge_intelligence(
    existing: Dict[str, List[str]], 
    new: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """
    Merge new extracted intelligence with existing data
    
    Args:
        existing: Current intelligence dictionary
        new: Newly extracted intelligence
        
    Returns:
        Merged intelligence dictionary with unique values
    """
    merged = {}
    
    # Get all unique keys
    all_keys = set(existing.keys()) | set(new.keys())
    
    for key in all_keys:
        existing_values = existing.get(key, [])
        new_values = new.get(key, [])
        
        # Combine and deduplicate
        merged[key] = list(set(existing_values + new_values))
    
    return merged