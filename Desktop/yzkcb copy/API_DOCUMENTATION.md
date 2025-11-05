# Yazaki Chatbot - Flask REST API Documentation

## Overview

The Yazaki Supplier Quality Chatbot provides an AI-powered assistant for automotive quality processes, PPAP requirements, APQP guidance, and supplier quality standards through a REST API interface.

## Quick Start

### Prerequisites
- Python 3.8+
- MongoDB
- Ollama (for LLM)

### Installation
```bash
# Clone repository
git clone <repository-url>
cd yazaki-chatbot

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp env.txt .env
# Edit .env with your configuration
```

### Start Services
```bash
# Start MongoDB
./start_mongodb.sh

# Initialize and start Flask API
python backend/api.py
```

### Access Web Interface
Open browser to: http://localhost:8000/

## API Reference

### Base URL
```
http://localhost:8000/api
```

### Authentication
Currently no authentication required. For production deployment, implement API keys or OAuth.

---

## Endpoints

### `POST /api/chat`
Send a message to the chatbot and receive a synchronous response.

**Request:**
```json
{
  "session_id": "optional-session-identifier",
  "history": [
    {"role": "user", "content": "What is PPAP?"},
    {"role": "assistant", "content": "PPAP is Production Part Approval Process..."}
  ],
  "message": "What are the PPAP submission levels?",
  "user_state": {
    "form_completed": true,
    "full_name": "Jane Engineer",
    "company_name": "ABC Manufacturing",
    "project_name": "Brake Component Project",
    "supplier_type": "Tier 1"
  }
}
```

**Response:**
```json
{
  "reply": "PPAP submission levels are defined as follows: Level 1 - Part submission warrant only...",
  "session_id": "abc123-def456-ghi789",
  "metadata": {
    "sources": ["Supplier_Quality_Manual", "PPAP_Guidelines"],
    "response_time": 2.3,
    "timestamp": "14:30",
    "num_documents_retrieved": 5
  }
}
```

**Error Response:**
```json
{
  "error": "Missing required field: 'message'"
}
```

### `POST /api/stream`
Send a message and receive streaming response chunks via Server-Sent Events.

**Request:** Same as `/api/chat`

**Response Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Response Stream:**
```
data: {"status": "retrieving", "session_id": "abc123"}

data: {"status": "generating", "session_id": "abc123"}

data: {"chunk": "PPAP submission", "accumulated": "PPAP submission", "done": false}

data: {"chunk": " levels are", "accumulated": "PPAP submission levels are", "done": false}

data: {"chunk": "", "accumulated": "Complete response text...", "done": true, "metadata": {...}}

data: [DONE]
```

### `POST /api/init`
Initialize the system database and vector store. Idempotent operation.

**Request:**
```json
{
  "vector_store_name": "vector_store_json"
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "System initialized successfully",
  "details": {
    "mongodb": {"status": "connected"},
    "vector_store": {"status": "initialized"},
    "overall": "healthy"
  }
}
```

### `GET /api/health`
Check system health and component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00.000000",
  "details": {
    "mongodb": {
      "status": "connected",
      "details": {
        "database": "yazaki_chatbot",
        "conversations_count": 1250,
        "sessions_count": 89
      }
    },
    "vector_store": {
      "status": "initialized",
      "details": {
        "retriever_available": true,
        "test_results_count": 1
      }
    },
    "overall": "healthy"
  }
}
```

### `GET /api/models`
List available LLM models and current selection.

**Response:**
```json
{
  "models": ["gemma3:4b", "mistral:latest", "llama2:7b"],
  "current": "gemma3:4b"
}
```

### `GET /api/sessions/{session_id}`
Get information about a specific session.

**Response:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "active": true,
  "details": {
    "created_at": "2024-01-01T10:00:00",
    "last_active": "2024-01-01T10:30:00",
    "message_count": 5
  }
}
```

### `GET /api`
Get API information and endpoint documentation.

**Response:**
```json
{
  "name": "Yazaki Chatbot API",
  "version": "1.0.0",
  "description": "REST API for Yazaki Supplier Quality Chatbot",
  "endpoints": {
    "POST /api/chat": "Synchronous chat responses",
    "POST /api/stream": "Streaming chat responses (SSE)",
    "POST /api/init": "Initialize database and vector store",
    "GET /api/health": "System health check",
    "GET /api/models": "List available LLM models"
  }
}
```

---

## Data Models

### Chat Message
```typescript
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
```

### User State
```typescript
interface UserState {
  form_completed: boolean;
  full_name?: string;
  email?: string;
  company_name?: string;
  project_name?: string;
  supplier_type?: string;
  city?: string;
  country?: string;
}
```

### Chat Request
```typescript
interface ChatRequest {
  session_id?: string;
  history: ChatMessage[];
  message: string;
  user_state: UserState;
}
```

### Chat Response
```typescript
interface ChatResponse {
  reply: string;
  session_id: string;
  metadata?: {
    sources: string[];
    response_time: number;
    timestamp: string;
    num_documents_retrieved: number;
  };
}
```

---

## Error Codes

| Code | Description | Example |
|------|-------------|---------|
| 400 | Bad Request | Missing required field, invalid JSON |
| 401 | Unauthorized | Session validation failed |
| 404 | Not Found | Endpoint or resource not found |
| 500 | Internal Server Error | Database connection error, LLM failure |
| 503 | Service Unavailable | System not initialized |

---

## Configuration

### Environment Variables

```bash
# Flask Configuration
FLASK_ENV=development          # development, production, testing
FLASK_HOST=0.0.0.0            # Host interface
FLASK_PORT=8000               # Port number
FLASK_DEBUG=true              # Enable debug mode

# CORS Configuration  
CORS_ORIGINS=*                # Allowed origins (* for development)

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=yazaki_chatbot
MONGODB_CONVERSATIONS=conversations

# LLM Configuration
LLM_MODEL=gemma3:4b           # Ollama model name
LLM_TEMPERATURE=0.3           # Response creativity (0.0-1.0)
LLM_MAX_TOKENS=400            # Maximum response length
OLLAMA_BASE_URL=http://localhost:11434

# Embeddings Configuration
EMBEDDING_MODEL=balanced      # Embedding model variant
CHUNK_SIZE=500                # Document chunk size
CHUNK_OVERLAP=100             # Chunk overlap

# Data Paths
VECTOR_STORE_PATH=data/processed/vector_store
PDF_DATA_PATH=data/pdf_backup

# Session Configuration
SESSION_TIMEOUT_MINUTES=30    # Session timeout
SESSION_MONITOR_INTERVAL_SECONDS=30
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "backend/api.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
  
  chatbot-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/
      - FLASK_ENV=production
    depends_on:
      - mongodb

volumes:
  mongodb_data:
```

---

## Client Examples

### JavaScript/Browser
```javascript
class YazakiClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.sessionId = null;
  }

  async chat(message, history = []) {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history,
        session_id: this.sessionId,
        user_state: { form_completed: true }
      })
    });

    const data = await response.json();
    if (data.session_id) this.sessionId = data.session_id;
    return data;
  }

  async streamChat(message, onChunk) {
    const response = await fetch(`${this.baseUrl}/api/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: this.sessionId,
        user_state: { form_completed: true }
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          onChunk(data);
          if (data.done) return;
        }
      }
    }
  }
}

// Usage
const client = new YazakiClient();
const response = await client.chat('What is PPAP?');
console.log(response.reply);
```

### Python Client
```python
import requests
import json

class YazakiClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def chat(self, message, history=None):
        url = f"{self.base_url}/api/chat"
        payload = {
            "message": message,
            "history": history or [],
            "session_id": self.session_id,
            "user_state": {"form_completed": True}
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if "session_id" in data:
            self.session_id = data["session_id"]
        
        return data
    
    def health_check(self):
        response = requests.get(f"{self.base_url}/api/health")
        return response.json()

# Usage
client = YazakiClient()
response = client.chat("What are APQP phases?")
print(response["reply"])
```

### cURL Examples

See `tests/curl_examples.md` for comprehensive cURL examples.

---

## Deployment

### Production Setup

1. **Environment Configuration:**
```bash
export FLASK_ENV=production
export FLASK_DEBUG=false
export CORS_ORIGINS=https://yourdomain.com
export SECRET_KEY=$(openssl rand -base64 32)
```

2. **Database Setup:**
```bash
# Production MongoDB with authentication
export MONGODB_URI="mongodb://user:pass@prod-mongo:27017/yazaki_chatbot?authSource=admin"
```

3. **Process Management:**
```bash
# Using gunicorn for production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "backend.api:create_app()"

# Or using systemd service
sudo systemctl start yazaki-chatbot
```

4. **Reverse Proxy (nginx):**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
    }
}
```

---

## Monitoring

### Health Monitoring
```bash
# Check system health
curl http://localhost:8000/api/health

# Monitor logs
tail -f logs/chatbot.jsonl
tail -f logs/chatbot_errors.log
```

### Metrics Collection
Key metrics to monitor:
- Response time (available in `/api/health`)
- Success rate (2xx vs 4xx/5xx responses)
- Active sessions count
- Database connection status
- Vector store query performance

### Log Analysis
```bash
# Analyze conversation logs
jq '.user_message' logs/chatbot.jsonl | head -10

# Check error patterns
grep ERROR logs/chatbot_errors.log

# Session statistics
jq '.session_id' logs/chatbot.jsonl | sort | uniq -c
```

---

## Troubleshooting

### Common Issues

**1. "System not initialized"**
```bash
# Solution: Initialize system
curl -X POST http://localhost:8000/api/init \
  -H "Content-Type: application/json" \
  -d '{}'
```

**2. "Database connection failed"**
```bash
# Check MongoDB status
systemctl status mongod
# Or start MongoDB
./start_mongodb.sh
```

**3. "LLM model not found"**
```bash
# Check available models
ollama list
# Pull required model  
ollama pull gemma3:4b
```

**4. "Vector store not found"**
```bash
# Rebuild vector store
python scripts/embed_json_data.py
```

### Debug Mode
```bash
export FLASK_DEBUG=true
python backend/api.py
# Detailed error messages and stack traces will be shown
```

---

## Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
./tests/acceptance_tests.sh
python tests/behavioral_tests.py

# Code formatting
black backend/
flake8 backend/
```

### API Changes
When modifying the API:
1. Update this documentation
2. Add/update tests in `tests/`
3. Update client examples
4. Consider backward compatibility
5. Update version number

---

## Support

### Documentation
- API Reference: This document
- Migration Guide: `MIGRATION_GUIDE.md`
- Test Examples: `tests/curl_examples.md`

### Issues
For bug reports and feature requests, please create issues with:
- API endpoint being used
- Request/response examples
- Error messages or logs
- Expected vs actual behavior

### Contact
- Technical questions: [contact information]
- Documentation updates: [contact information]