# Yazaki Chatbot - Migration to Flask REST API

## Overview

This migration decouples the chat UI from backend logic, extracting all backend functionality from `frontend/gradio_app/enhanced_gradio.py` into dedicated Flask REST API modules under `backend/`.

## Architecture Changes

### Before (Gradio-based)
```
frontend/gradio_app/enhanced_gradio.py
├── MongoDB connection
├── Vector store initialization  
├── LLM management
├── Chat processing
├── Session management
└── UI components (Gradio)
```

### After (Flask REST API)
```
backend/
├── api.py                 # Flask app factory
├── db.py                  # Database & vector store management
├── routes/
│   └── chat.py           # REST API endpoints
├── services/
│   └── chat_service.py   # Chat logic & LLM processing
└── utils/
    └── logging_utils.py  # Centralized logging

frontend/static/
├── index.html            # Static HTML/CSS UI
└── chat.js              # JavaScript API client
```

## New Endpoints

### `POST /api/chat` - Synchronous Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "optional-session-id",
    "history": [{"role": "user", "content": "previous message"}],
    "message": "What is PPAP?",
    "user_state": {
      "form_completed": true,
      "full_name": "John Doe",
      "company_name": "ABC Corp"
    }
  }'
```

**Response:**
```json
{
  "reply": "PPAP (Production Part Approval Process) is...",
  "session_id": "generated-session-id",
  "metadata": {
    "sources": ["Supplier_Quality_Manual"],
    "response_time": 2.3,
    "timestamp": "14:30"
  }
}
```

### `POST /api/stream` - Server-Sent Events
```bash
curl -X POST http://localhost:8000/api/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -N \
  -d '{"message": "Explain APQP phases", "user_state": {"form_completed": true}}'
```

**Streaming Response:**
```
data: {"status": "retrieving", "session_id": "abc123"}
data: {"chunk": "APQP consists", "accumulated": "APQP consists", "done": false}
data: {"chunk": " of 5 phases", "accumulated": "APQP consists of 5 phases", "done": false}
data: {"chunk": "", "accumulated": "APQP consists of 5 phases...", "done": true, "metadata": {...}}
data: [DONE]
```

### `POST /api/init` - System Initialization
```bash
curl -X POST http://localhost:8000/api/init \
  -H "Content-Type: application/json" \
  -d '{"vector_store_name": "vector_store_json"}'
```

### `GET /api/health` - Health Check
```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00.000000",
  "details": {
    "mongodb": {"status": "connected", "details": {"conversations_count": 150}},
    "vector_store": {"status": "initialized", "details": {"retriever_available": true}},
    "overall": "healthy"
  }
}
```

## Migration Checklist

### ✅ Completed
- [x] Extract MongoDB connection logic → `backend/db.py`
- [x] Extract chat processing logic → `backend/services/chat_service.py`
- [x] Extract logging functionality → `backend/utils/logging_utils.py`
- [x] Create Flask REST API routes → `backend/routes/chat.py`
- [x] Create Flask app factory → `backend/api.py`
- [x] Create static HTML/JS frontend → `frontend/static/`
- [x] Create comprehensive test suite → `tests/`
- [x] Update requirements.txt with Flask dependencies

### 🔄 Next Steps
- [ ] Test MongoDB connection with new backend
- [ ] Verify vector store loading with new architecture
- [ ] Test all API endpoints with acceptance tests
- [ ] Migrate any custom session management logic
- [ ] Update deployment scripts for Flask app
- [ ] Remove Gradio dependency after validation

### ⚠️ Backward Compatibility
- `frontend/gradio_app/enhanced_gradio.py` marked as deprecated (TODO comment added)
- Keep Gradio imports commented in requirements.txt until migration validated
- Original app.py remains unchanged for fallback

## Configuration

### Environment Variables
```bash
# Flask Configuration
FLASK_ENV=development
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=true

# CORS Configuration
CORS_ORIGINS=*

# Database Configuration (existing)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=yazaki_chatbot

# LLM Configuration (existing)
LLM_MODEL=gemma3:4b
LLM_TEMPERATURE=0.3
OLLAMA_BASE_URL=http://localhost:11434
```

## Running the New Backend

### Development Mode
```bash
# Start MongoDB
./start_mongodb.sh

# Run Flask backend
cd backend
python api.py

# Or using Flask CLI
export FLASK_APP=backend.api:create_app
flask run --host=0.0.0.0 --port=8000
```

### Testing
```bash
# Run acceptance tests
./tests/acceptance_tests.sh

# Run behavioral tests
python tests/behavioral_tests.py

# Test specific endpoints
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","user_state":{"form_completed":true}}'
```

### Static Frontend
Access the web interface at: http://localhost:8000/

## API Contract

### Request Format
All POST endpoints expect `Content-Type: application/json`:
```json
{
  "session_id": "string (optional - will be generated if missing)",
  "history": [
    {"role": "user|assistant", "content": "message text"}
  ],
  "message": "string (required)",
  "user_state": {
    "form_completed": true,
    "full_name": "string (optional)",
    "company_name": "string (optional)",
    "project_name": "string (optional)"
  }
}
```

### Response Format
```json
{
  "reply": "string (assistant response)",
  "session_id": "string (session identifier)",
  "metadata": {
    "sources": ["array of referenced documents"],
    "response_time": 2.5,
    "timestamp": "HH:MM",
    "num_documents_retrieved": 5
  }
}
```

### Error Format
```json
{
  "error": "string (error description)",
  "message": "string (optional detailed message)"
}
```

## Testing Strategy

### Acceptance Tests (`tests/acceptance_tests.sh`)
- API endpoint availability
- System initialization idempotency  
- Basic chat functionality
- Input validation
- Error handling
- Session management

### Behavioral Tests (`tests/behavioral_tests.py`)
- Session persistence across requests
- Conversation logging verification
- Response format validation
- Edge case handling
- Streaming functionality

### Manual Testing
1. Start MongoDB: `./start_mongodb.sh`
2. Start Flask backend: `python backend/api.py`
3. Open browser: http://localhost:8000/
4. Test chat functionality through web interface
5. Verify logging in `logs/chatbot.jsonl`

## Architecture Benefits

### Decoupling Benefits
- **Frontend flexibility**: Can swap UI frameworks without backend changes
- **API-first**: Enables mobile apps, integrations, and third-party clients
- **Scalability**: Backend can be deployed independently with load balancing
- **Testing**: Clear separation allows independent testing of frontend/backend

### Maintainability  
- **Single responsibility**: Each module has focused functionality
- **Dependency isolation**: Database changes don't affect UI, and vice versa
- **Error handling**: Centralized error responses and logging
- **Documentation**: Clear API contract with examples

### Development Workflow
- **Parallel development**: Frontend and backend teams can work independently
- **API mocking**: Frontend development can use mock responses
- **Deployment flexibility**: Different deployment strategies for UI vs API

## Rollback Plan

If issues arise during migration:

1. **Immediate fallback**: Use existing `frontend/gradio_app/enhanced_gradio.py`
2. **Gradio restoration**: Uncomment gradio in requirements.txt
3. **Original startup**: Use existing app.py startup process

The old system remains untouched for safety during transition.

## Commit Strategy

Suggested commit messages:
```bash
git add backend/db.py backend/utils/logging_utils.py
git commit -m "feat: extract database and logging modules from gradio app"

git add backend/services/chat_service.py
git commit -m "feat: extract chat processing logic into dedicated service"

git add backend/routes/chat.py backend/api.py  
git commit -m "feat: implement Flask REST API with chat endpoints"

git add frontend/static/
git commit -m "feat: create static HTML/JS frontend for API consumption"

git add tests/
git commit -m "test: add comprehensive acceptance and behavioral tests"

git add requirements.txt
git commit -m "chore: update dependencies for Flask API migration"

git add MIGRATION_GUIDE.md
git commit -m "docs: add migration guide and API documentation"
```

## PR Checklist

- [ ] All backend logic extracted from enhanced_gradio.py
- [ ] Flask API endpoints implemented and tested
- [ ] Static frontend created and functional
- [ ] Database initialization working correctly
- [ ] Vector store loading successful
- [ ] Session management preserved
- [ ] Logging functionality maintained
- [ ] Error handling comprehensive
- [ ] Tests passing (acceptance + behavioral)
- [ ] Documentation complete
- [ ] Environment variables documented
- [ ] Rollback plan validated