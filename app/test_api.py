#!/usr/bin/env python3
"""
Test script for Honeypot API
Run this after starting the server to verify it's working correctly
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "honeypot-secret-key-2025-guvi-hackathon"

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}


def test_health_check():
    """Test basic health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_scam_detection():
    """Test scam message detection and response"""
    print("\n" + "="*60)
    print("TEST 2: Scam Detection & Agent Response")
    print("="*60)
    
    session_id = f"test-session-{int(time.time())}"
    
    # Message 1: Initial scam attempt
    payload1 = {
        "sessionId": session_id,
        "message": {
            "sender": "scammer",
            "text": "URGENT! Your bank account will be blocked today. Verify immediately by sharing your OTP.",
            "timestamp": int(time.time() * 1000)
        },
        "conversationHistory": [],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        }
    }
    
    try:
        print(f"\nSession ID: {session_id}")
        print(f"Scammer Message: {payload1['message']['text']}")
        
        response = requests.post(
            f"{API_BASE_URL}/honeypot/message",
            headers=HEADERS,
            json=payload1
        )
        
        print(f"\nStatus Code: {response.status_code}")
        result = response.json()
        print(f"Agent Reply: {result['reply']}")
        
        assert response.status_code == 200
        assert result["status"] == "success"
        assert len(result["reply"]) > 0
        
        print("\n✅ Message 1 PASSED")
        
        # Message 2: Follow-up
        time.sleep(2)  # Small delay for realistic conversation
        
        payload2 = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": "Send your UPI ID to refund@scam. Also install AnyDesk app for remote verification.",
                "timestamp": int(time.time() * 1000)
            },
            "conversationHistory": [
                payload1["message"],
                {
                    "sender": "user",
                    "text": result["reply"],
                    "timestamp": payload1["message"]["timestamp"] + 1000
                }
            ],
            "metadata": payload1["metadata"]
        }
        
        print(f"\n--- Follow-up Message ---")
        print(f"Scammer: {payload2['message']['text']}")
        
        response2 = requests.post(
            f"{API_BASE_URL}/honeypot/message",
            headers=HEADERS,
            json=payload2
        )
        
        result2 = response2.json()
        print(f"Agent Reply: {result2['reply']}")
        
        assert response2.status_code == 200
        
        print("\n✅ Message 2 PASSED")
        
        # Check session info
        session_response = requests.get(
            f"{API_BASE_URL}/honeypot/session/{session_id}",
            headers=HEADERS
        )
        
        session_info = session_response.json()
        print("\n--- Session Intelligence ---")
        print(json.dumps(session_info, indent=2))
        
        assert session_info["scamDetected"] == True
        assert session_info["totalMessages"] >= 4
        
        print("\n✅ TEST 2 FULLY PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_key_validation():
    """Test API key authentication"""
    print("\n" + "="*60)
    print("TEST 3: API Key Validation")
    print("="*60)
    
    # Test without API key
    try:
        response = requests.post(
            f"{API_BASE_URL}/honeypot/message",
            json={"sessionId": "test", "message": {"sender": "scammer", "text": "test", "timestamp": 123}}
        )
        
        print(f"Without API key - Status: {response.status_code}")
        assert response.status_code == 401
        print("✅ Correctly rejected request without API key")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    
    # Test with wrong API key
    try:
        wrong_headers = {
            "x-api-key": "wrong-key",
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{API_BASE_URL}/honeypot/message",
            headers=wrong_headers,
            json={"sessionId": "test", "message": {"sender": "scammer", "text": "test", "timestamp": 123}}
        )
        
        print(f"With wrong API key - Status: {response.status_code}")
        assert response.status_code == 403
        print("✅ Correctly rejected request with wrong API key")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    
    print("\n✅ TEST 3 PASSED")
    return True


def test_stats_endpoint():
    """Test stats endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Stats Endpoint")
    print("="*60)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/honeypot/stats",
            headers=HEADERS
        )
        
        print(f"Status: {response.status_code}")
        stats = response.json()
        print(f"Stats: {json.dumps(stats, indent=2)}")
        
        assert response.status_code == 200
        assert "activeSessions" in stats
        
        print("✅ PASSED")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_non_scam_message():
    """Test legitimate message handling"""
    print("\n" + "="*60)
    print("TEST 5: Non-Scam Message Handling")
    print("="*60)
    
    session_id = f"test-legit-{int(time.time())}"
    
    payload = {
        "sessionId": session_id,
        "message": {
            "sender": "scammer",  # Testing if it correctly identifies as non-scam
            "text": "Hello, how are you today?",
            "timestamp": int(time.time() * 1000)
        },
        "conversationHistory": [],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/honeypot/message",
            headers=HEADERS,
            json=payload
        )
        
        result = response.json()
        print(f"Message: {payload['message']['text']}")
        print(f"Reply: {result['reply']}")
        
        # Check session wasn't marked as scam
        session_response = requests.get(
            f"{API_BASE_URL}/honeypot/session/{session_id}",
            headers=HEADERS
        )
        
        session_info = session_response.json()
        print(f"Scam Detected: {session_info['scamDetected']}")
        
        # Should not engage deeply with non-scam
        assert session_info['scamDetected'] == False
        
        print("✅ PASSED")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("HONEYPOT API TEST SUITE")
    print("="*60)
    print("\nMake sure the server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    input()
    
    results = []
    
    # Run all tests
    results.append(("Health Check", test_health_check()))
    results.append(("Scam Detection", test_scam_detection()))
    results.append(("API Key Validation", test_api_key_validation()))
    results.append(("Stats Endpoint", test_stats_endpoint()))
    results.append(("Non-Scam Handling", test_non_scam_message()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! API is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.")


if __name__ == "__main__":
    main()