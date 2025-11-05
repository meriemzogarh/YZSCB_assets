# Yazaki Chatbot REST API - cURL Examples

This document provides practical cURL examples for testing and using the Yazaki Chatbot REST API.

## Base Configuration

```bash
# Set your base URL
export API_BASE="http://localhost:8000"

# Generate a test session ID
export TEST_SESSION="test-$(date +%s)"
```

## 1. System Health Check

Check if the API is running and get system status:

```bash
curl -X GET "$API_BASE/api/health" \
  -H "Accept: application/json"
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00.000000",
  "details": {
    "mongodb": {"status": "connected"},
    "vector_store": {"status": "initialized"},
    "overall": "healthy"
  }
}
```

## 2. Initialize System

Initialize the database and vector store:

```bash
curl -X POST "$API_BASE/api/init" \
  -H "Content-Type: application/json" \
  -d '{
    "vector_store_name": "vector_store_json"
  }'
```

Expected response:
```json
{
  "status": "ok",
  "message": "System initialized successfully",
  "details": {...}
}
```

## 3. Basic Chat Request

Send a simple chat message:

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is PPAP?",
    "session_id": "'$TEST_SESSION'",
    "history": [],
    "user_state": {
      "form_completed": true,
      "full_name": "John Supplier",
      "company_name": "ABC Manufacturing"
    }
  }'
```

Expected response:
```json
{
  "reply": "PPAP (Production Part Approval Process) is...",
  "session_id": "test-1234567890",
  "metadata": {
    "sources": ["Supplier_Quality_Manual"],
    "response_time": 2.5,
    "timestamp": "10:30"
  }
}
```

## 4. Follow-up Chat Message

Continue a conversation with history:

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the PPAP submission levels?",
    "session_id": "'$TEST_SESSION'",
    "history": [
      {"role": "user", "content": "What is PPAP?"},
      {"role": "assistant", "content": "PPAP (Production Part Approval Process) is..."}
    ],
    "user_state": {
      "form_completed": true,
      "full_name": "John Supplier",
      "company_name": "ABC Manufacturing"
    }
  }'
```

## 5. Streaming Chat Request

Get streaming response using Server-Sent Events:

```bash
curl -X POST "$API_BASE/api/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -N \
  -d '{
    "message": "Explain the APQP process phases",
    "session_id": "'$TEST_SESSION'",
    "history": [],
    "user_state": {"form_completed": true}
  }'
```

Expected streaming output:
```
data: {"status": "retrieving", "session_id": "test-123"}

data: {"status": "generating", "session_id": "test-123"}

data: {"chunk": "APQP (Advanced", "accumulated": "APQP (Advanced", "done": false}

data: {"chunk": "Product Quality Planning)", "accumulated": "APQP (Advanced Product Quality Planning)", "done": false}

...

data: {"chunk": "", "accumulated": "Full response text here", "done": true, "metadata": {...}}

data: [DONE]
```

## 6. Check Available Models

List available LLM models:

```bash
curl -X GET "$API_BASE/api/models" \
  -H "Accept: application/json"
```

Expected response:
```json
{
  "models": ["gemma3:4b", "mistral:latest"],
  "current": "gemma3:4b"
}
```

## 7. Get Session Information

Check session status and details:

```bash
curl -X GET "$API_BASE/api/sessions/$TEST_SESSION" \
  -H "Accept: application/json"
```

Expected response:
```json
{
  "session_id": "test-1234567890",
  "active": true,
  "details": {
    "created_at": "2024-01-01T10:00:00",
    "last_active": "2024-01-01T10:30:00"
  }
}
```

## 8. API Information

Get API endpoint documentation:

```bash
curl -X GET "$API_BASE/api" \
  -H "Accept: application/json"
```

## Error Handling Examples

### Missing Required Field

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "'$TEST_SESSION'",
    "history": []
  }'
```

Response (400 Bad Request):
```json
{
  "error": "Missing required field: 'message'"
}
```

### Empty Message

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "",
    "session_id": "'$TEST_SESSION'",
    "history": []
  }'
```

Response (400 Bad Request):
```json
{
  "error": "Message cannot be empty"
}
```

### Invalid JSON

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"invalid": json}'
```

Response (400 Bad Request):
```json
{
  "error": "Content-Type must be application/json"
}
```

## Advanced Examples

### Complex Question with Context

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We are implementing APQP for a new automotive component. What documentation is required for Phase 3 planning?",
    "session_id": "'$TEST_SESSION'",
    "history": [
      {"role": "user", "content": "What are the APQP phases?"},
      {"role": "assistant", "content": "APQP consists of 5 phases: Phase 1 - Planning, Phase 2 - Product Design, Phase 3 - Process Design, Phase 4 - Product Validation, Phase 5 - Launch."}
    ],
    "user_state": {
      "form_completed": true,
      "full_name": "Jane Engineer",
      "company_name": "XYZ Automotive",
      "project_name": "New Brake Component",
      "supplier_type": "Tier 1"
    }
  }'
```

### Quality-Specific Query

```bash
curl -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the requirements for supplier change management and SICR process?",
    "session_id": "'$TEST_SESSION'",
    "history": [],
    "user_state": {
      "form_completed": true,
      "full_name": "Quality Manager",
      "company_name": "Supplier Corp"
    }
  }'
```

## Testing Scripts

### Quick Health Check Script

```bash
#!/bin/bash
echo "Testing Yazaki Chatbot API..."
response=$(curl -s "$API_BASE/api/health")
status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
echo "API Status: $status"

if [ "$status" = "healthy" ]; then
    echo "✅ API is ready for use"
else
    echo "⚠️ API may need initialization"
fi
```

### Initialize and Test Script

```bash
#!/bin/bash
API_BASE="http://localhost:8000"

echo "1. Initializing system..."
curl -s -X POST "$API_BASE/api/init" \
  -H "Content-Type: application/json" \
  -d '{}' > /dev/null

echo "2. Testing chat..."
response=$(curl -s -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, test message",
    "user_state": {"form_completed": true}
  }')

if echo "$response" | grep -q "reply"; then
    echo "✅ Chat API working correctly"
else
    echo "❌ Chat API test failed"
    echo "$response"
fi
```

## Notes

- Replace `$API_BASE` with your actual API URL (e.g., `https://your-domain.com`)
- Set appropriate `CORS_ORIGINS` environment variable for cross-origin requests
- The `user_state.form_completed` field should be `true` for API requests
- Session IDs are optional; the API will generate one if not provided
- Streaming responses require SSE-compatible clients (use `-N` flag with cURL)