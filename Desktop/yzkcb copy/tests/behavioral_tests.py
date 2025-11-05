#!/usr/bin/env python3
"""
Behavioral assertion tests for Yazaki Chatbot API
Tests specific behavioral requirements and edge cases
"""

import requests
import json
import time
import uuid
from typing import Dict, Any, Optional

class YazakiAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"test-{uuid.uuid4()}"
        self.test_results = []
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
    
    def make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)
        
        try:
            if method == "GET":
                return requests.get(url, headers=default_headers)
            elif method == "POST":
                return requests.post(url, json=data, headers=default_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
        except requests.ConnectionError:
            raise ConnectionError(f"Could not connect to {url}")
    
    def test_api_availability(self):
        """Test if API is accessible"""
        try:
            response = self.make_request("/api/health")
            passed = response.status_code == 200
            self.log_test("API Availability", passed, 
                         f"Status: {response.status_code}")
            return passed
        except Exception as e:
            self.log_test("API Availability", False, str(e))
            return False
    
    def test_system_initialization(self):
        """Test system initialization is idempotent"""
        try:
            # Initialize once
            response1 = self.make_request("/api/init", "POST", 
                                        {"vector_store_name": "vector_store_json"})
            
            # Initialize again (should be idempotent)
            response2 = self.make_request("/api/init", "POST", 
                                        {"vector_store_name": "vector_store_json"})
            
            passed = (response1.status_code == 200 and response2.status_code == 200)
            self.log_test("System Initialization Idempotency", passed,
                         f"First: {response1.status_code}, Second: {response2.status_code}")
            return passed
        except Exception as e:
            self.log_test("System Initialization Idempotency", False, str(e))
            return False
    
    def test_chat_session_persistence(self):
        """Test that session ID is maintained across requests"""
        try:
            # First message
            data1 = {
                "message": "What is PPAP?",
                "session_id": self.session_id,
                "history": [],
                "user_state": {"form_completed": True}
            }
            response1 = self.make_request("/api/chat", "POST", data1)
            
            if response1.status_code != 200:
                self.log_test("Chat Session Persistence", False, 
                             f"First request failed: {response1.status_code}")
                return False
            
            result1 = response1.json()
            returned_session = result1.get("session_id")
            
            # Second message with same session
            data2 = {
                "message": "What are the PPAP levels?", 
                "session_id": returned_session,
                "history": [
                    {"role": "user", "content": "What is PPAP?"},
                    {"role": "assistant", "content": result1["reply"]}
                ],
                "user_state": {"form_completed": True}
            }
            response2 = self.make_request("/api/chat", "POST", data2)
            
            if response2.status_code == 200:
                result2 = response2.json()
                session_maintained = result2.get("session_id") == returned_session
                self.log_test("Chat Session Persistence", session_maintained,
                             f"Session ID maintained: {session_maintained}")
                return session_maintained
            else:
                self.log_test("Chat Session Persistence", False,
                             f"Second request failed: {response2.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Chat Session Persistence", False, str(e))
            return False
    
    def test_conversation_logging(self):
        """Test that conversations are logged properly"""
        try:
            data = {
                "message": "Test logging message",
                "session_id": f"log-test-{uuid.uuid4()}",
                "history": [],
                "user_state": {
                    "form_completed": True,
                    "full_name": "Test User",
                    "company_name": "Test Company"
                }
            }
            
            response = self.make_request("/api/chat", "POST", data)
            
            passed = response.status_code == 200
            if passed:
                result = response.json()
                # Check if response has metadata indicating logging
                has_metadata = "metadata" in result
                self.log_test("Conversation Logging", has_metadata,
                             f"Response includes metadata: {has_metadata}")
                return has_metadata
            else:
                self.log_test("Conversation Logging", False,
                             f"Chat request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Conversation Logging", False, str(e))
            return False
    
    def test_input_validation(self):
        """Test various input validation scenarios"""
        test_cases = [
            {
                "name": "Empty Message",
                "data": {"message": "", "user_state": {"form_completed": True}},
                "expected_status": 400
            },
            {
                "name": "Missing Message",
                "data": {"user_state": {"form_completed": True}},
                "expected_status": 400
            },
            {
                "name": "Very Long Message",
                "data": {
                    "message": "A" * 10000,
                    "user_state": {"form_completed": True}
                },
                "expected_status": 200  # Should handle long messages
            },
            {
                "name": "Unicode Characters",
                "data": {
                    "message": "What about émojis 🚗 and ünïcödé?",
                    "user_state": {"form_completed": True}
                },
                "expected_status": 200
            }
        ]
        
        all_passed = True
        for case in test_cases:
            try:
                response = self.make_request("/api/chat", "POST", case["data"])
                passed = response.status_code == case["expected_status"]
                self.log_test(f"Input Validation - {case['name']}", passed,
                             f"Expected {case['expected_status']}, got {response.status_code}")
                if not passed:
                    all_passed = False
            except Exception as e:
                self.log_test(f"Input Validation - {case['name']}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_response_format(self):
        """Test that responses have correct format"""
        try:
            data = {
                "message": "What is quality management?",
                "user_state": {"form_completed": True}
            }
            
            response = self.make_request("/api/chat", "POST", data)
            
            if response.status_code != 200:
                self.log_test("Response Format", False, 
                             f"Request failed: {response.status_code}")
                return False
            
            result = response.json()
            
            # Check required fields
            required_fields = ["reply", "session_id"]
            missing_fields = [field for field in required_fields 
                            if field not in result]
            
            if missing_fields:
                self.log_test("Response Format", False,
                             f"Missing fields: {missing_fields}")
                return False
            
            # Check response content quality
            reply = result["reply"]
            reply_checks = [
                ("Non-empty reply", len(reply.strip()) > 0),
                ("Reasonable length", 10 < len(reply) < 5000),
                ("English text", any(c.isalpha() for c in reply)),
                ("No raw error messages", "Exception" not in reply and "Traceback" not in reply)
            ]
            
            failed_checks = [check[0] for check in reply_checks if not check[1]]
            
            if failed_checks:
                self.log_test("Response Format", False,
                             f"Failed checks: {failed_checks}")
                return False
            
            self.log_test("Response Format", True, "All format checks passed")
            return True
            
        except Exception as e:
            self.log_test("Response Format", False, str(e))
            return False
    
    def test_error_handling(self):
        """Test proper error handling for various error conditions"""
        error_cases = [
            {
                "name": "Invalid JSON",
                "raw_data": '{"invalid": json}',
                "expected_status": 400
            },
            {
                "name": "Wrong Content-Type",
                "data": {"message": "test"},
                "headers": {"Content-Type": "text/plain"},
                "expected_status": 400
            }
        ]
        
        all_passed = True
        
        # Test invalid JSON
        try:
            url = f"{self.base_url}/api/chat"
            response = requests.post(url, data='{"invalid": json}',
                                   headers={"Content-Type": "application/json"})
            passed = response.status_code == 400
            self.log_test("Error Handling - Invalid JSON", passed,
                         f"Status: {response.status_code}")
            if not passed:
                all_passed = False
        except Exception as e:
            self.log_test("Error Handling - Invalid JSON", False, str(e))
            all_passed = False
        
        # Test wrong content type
        try:
            response = self.make_request("/api/chat", "POST", 
                                       {"message": "test"}, 
                                       {"Content-Type": "text/plain"})
            passed = response.status_code == 400
            self.log_test("Error Handling - Wrong Content-Type", passed,
                         f"Status: {response.status_code}")
            if not passed:
                all_passed = False
        except Exception as e:
            self.log_test("Error Handling - Wrong Content-Type", False, str(e))
            all_passed = False
        
        return all_passed
    
    def test_streaming_endpoint(self):
        """Test streaming chat endpoint basic functionality"""
        try:
            data = {
                "message": "Brief test message",
                "user_state": {"form_completed": True}
            }
            
            # Just test if streaming endpoint is accessible
            response = requests.post(f"{self.base_url}/api/stream", 
                                   json=data,
                                   headers={"Content-Type": "application/json"},
                                   stream=True,
                                   timeout=5)
            
            # For streaming, we just check if it starts correctly
            passed = response.status_code == 200
            content_type = response.headers.get('content-type', '')
            is_stream = 'event-stream' in content_type or 'stream' in content_type
            
            self.log_test("Streaming Endpoint", passed and is_stream,
                         f"Status: {response.status_code}, Content-Type: {content_type}")
            
            response.close()
            return passed and is_stream
            
        except requests.Timeout:
            self.log_test("Streaming Endpoint", False, "Request timeout")
            return False
        except Exception as e:
            self.log_test("Streaming Endpoint", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all behavioral tests"""
        print("🧪 Running Yazaki Chatbot Behavioral Tests")
        print("=" * 50)
        
        tests = [
            self.test_api_availability,
            self.test_system_initialization,
            self.test_chat_session_persistence,
            self.test_conversation_logging,
            self.test_input_validation,
            self.test_response_format,
            self.test_error_handling,
            self.test_streaming_endpoint
        ]
        
        passed_count = 0
        total_count = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_count += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
            print()  # Add spacing between tests
        
        print("📊 Test Summary")
        print("-" * 20)
        print(f"Total Tests: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")
        print(f"Success Rate: {(passed_count/total_count)*100:.1f}%")
        
        if passed_count == total_count:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n⚠️  {total_count - passed_count} tests failed.")
            return False

def main():
    """Main test runner"""
    import sys
    
    api_base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"Testing API at: {api_base}")
    print()
    
    tester = YazakiAPITester(api_base)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()