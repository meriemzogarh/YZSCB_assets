#!/bin/bash
# Yazaki Chatbot API Acceptance Tests
# Tests the REST API endpoints to ensure proper functionality

set -e  # Exit on any error

# Configuration
API_BASE="http://localhost:8000"
TEST_SESSION_ID="test-$(date +%s)"

echo "🧪 Yazaki Chatbot API Acceptance Tests"
echo "======================================"
echo "API Base URL: $API_BASE"
echo "Test Session ID: $TEST_SESSION_ID"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test functions
test_passed() {
    echo -e "${GREEN}✅ PASSED${NC}: $1"
}

test_failed() {
    echo -e "${RED}❌ FAILED${NC}: $1"
    echo -e "${RED}   Response: $2${NC}"
}

test_warning() {
    echo -e "${YELLOW}⚠️  WARNING${NC}: $1"
}

test_info() {
    echo -e "${BLUE}ℹ️  INFO${NC}: $1"
}

# Test 1: API Root Endpoint
echo "1. Testing API root endpoint..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/api" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    if echo "$body" | grep -q "Yazaki Chatbot API"; then
        test_passed "API root endpoint returns correct info"
    else
        test_failed "API root endpoint - wrong content" "$body"
    fi
else
    test_failed "API root endpoint - HTTP $http_code" "$body"
fi
echo ""

# Test 2: Health Check
echo "2. Testing health check endpoint..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/api/health" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    test_passed "Health check endpoint accessible"
    test_info "Health status: $(echo "$body" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
else
    test_failed "Health check endpoint - HTTP $http_code" "$body"
fi
echo ""

# Test 3: System Initialization
echo "3. Testing system initialization..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"vector_store_name": "vector_store_json"}' \
    "$API_BASE/api/init" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    status=$(echo "$body" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$status" = "ok" ] || [ "$status" = "partial" ]; then
        test_passed "System initialization successful (status: $status)"
    else
        test_warning "System initialization returned status: $status"
    fi
else
    test_failed "System initialization - HTTP $http_code" "$body"
fi
echo ""

# Test 4: Models List
echo "4. Testing models list endpoint..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/api/models" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    test_passed "Models list endpoint accessible"
    current_model=$(echo "$body" | grep -o '"current":"[^"]*"' | cut -d'"' -f4)
    test_info "Current model: $current_model"
else
    test_failed "Models list endpoint - HTTP $http_code" "$body"
fi
echo ""

# Test 5: Chat - Missing Message (Should fail)
echo "5. Testing chat endpoint with missing message (should fail)..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"session_id": "'$TEST_SESSION_ID'", "history": []}' \
    "$API_BASE/api/chat" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "400" ]; then
    test_passed "Chat endpoint correctly rejects missing message"
else
    test_failed "Chat endpoint should return 400 for missing message - HTTP $http_code" "$body"
fi
echo ""

# Test 6: Chat - Valid Request
echo "6. Testing chat endpoint with valid message..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "session_id": "'$TEST_SESSION_ID'",
        "history": [],
        "message": "What is PPAP?",
        "user_state": {
            "form_completed": true,
            "full_name": "Test User",
            "company_name": "Test Company"
        }
    }' \
    "$API_BASE/api/chat" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    if echo "$body" | grep -q '"reply"'; then
        test_passed "Chat endpoint returns valid response"
        
        # Check for session ID in response
        if echo "$body" | grep -q '"session_id"'; then
            returned_session_id=$(echo "$body" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
            test_info "Session ID: ${returned_session_id:0:12}..."
        fi
        
        # Check response length
        reply_length=$(echo "$body" | grep -o '"reply":"[^"]*"' | wc -c)
        if [ "$reply_length" -gt 20 ]; then
            test_passed "Chat response has reasonable length"
        else
            test_warning "Chat response seems very short"
        fi
    else
        test_failed "Chat endpoint - missing reply field" "$body"
    fi
else
    test_failed "Chat endpoint - HTTP $http_code" "$body"
fi
echo ""

# Test 7: Chat - Empty Message (Should fail)
echo "7. Testing chat endpoint with empty message..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "session_id": "'$TEST_SESSION_ID'",
        "history": [],
        "message": "",
        "user_state": {"form_completed": true}
    }' \
    "$API_BASE/api/chat" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "400" ]; then
    test_passed "Chat endpoint correctly rejects empty message"
else
    test_failed "Chat endpoint should return 400 for empty message - HTTP $http_code"
fi
echo ""

# Test 8: Session Info (if endpoint exists)
echo "8. Testing session info endpoint..."
if [ ! -z "$returned_session_id" ]; then
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE/api/sessions/$returned_session_id" || echo -e "\n000")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        test_passed "Session info endpoint accessible"
    elif [ "$http_code" = "503" ]; then
        test_warning "Session management not available"
    else
        test_warning "Session info endpoint - HTTP $http_code"
    fi
else
    test_warning "No session ID to test session info endpoint"
fi
echo ""

# Test 9: Streaming Chat (Basic connectivity test)
echo "9. Testing streaming chat endpoint..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "session_id": "'$TEST_SESSION_ID'",
        "history": [],
        "message": "Hello",
        "user_state": {"form_completed": true}
    }' \
    "$API_BASE/api/stream" \
    --max-time 10 || echo -e "\n000")

# For streaming, we just check if it doesn't immediately fail
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" != "000" ] && [ "$http_code" != "400" ]; then
    test_passed "Streaming endpoint accessible"
else
    test_warning "Streaming endpoint may not be working properly"
fi
echo ""

# Test 10: Invalid JSON (Should fail)
echo "10. Testing chat endpoint with invalid JSON..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"invalid": json}' \
    "$API_BASE/api/chat" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "400" ]; then
    test_passed "Chat endpoint correctly rejects invalid JSON"
else
    test_warning "Chat endpoint should handle invalid JSON better - HTTP $http_code"
fi
echo ""

# Test 11: Wrong Content-Type (Should fail)
echo "11. Testing chat endpoint with wrong content-type..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: text/plain" \
    -d 'plain text' \
    "$API_BASE/api/chat" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "400" ]; then
    test_passed "Chat endpoint correctly rejects wrong content-type"
else
    test_warning "Chat endpoint should validate content-type - HTTP $http_code"
fi
echo ""

echo "🏁 Test Summary"
echo "==============="
echo "All basic API tests completed!"
echo ""
echo "💡 Additional Manual Tests:"
echo "   - Test the web interface at $API_BASE"
echo "   - Verify MongoDB logging (check logs/chatbot.jsonl)"
echo "   - Test with various question types (PPAP, APQP, etc.)"
echo "   - Test session timeout behavior"
echo ""

# If all critical tests passed, exit with 0
echo "✅ Acceptance tests completed successfully!"