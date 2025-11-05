# Yazaki Chatbot - Enhanced Gradio (DEPRECATED)

## ⚠️ DEPRECATION NOTICE

**This file is deprecated as of the Flask REST API migration.** 

The functionality in this file has been extracted and reorganized into the new Flask backend architecture:

- **Database management** → `backend/db.py`
- **Chat processing** → `backend/services/chat_service.py`
- **Logging** → `backend/utils/logging_utils.py`
- **API routes** → `backend/routes/chat.py`
- **App factory** → `backend/api.py`
- **Frontend UI** → `frontend/static/`

## Migration Path

Instead of running this Gradio app, use the new Flask REST API:

```bash
# Old way (deprecated)
python frontend/gradio_app/enhanced_gradio.py

# New way (recommended)
python backend/api.py
# Then open: http://localhost:8000/
```

## Backward Compatibility

This file is kept temporarily for:
1. **Rollback capability** during migration period
2. **Reference implementation** for comparing behavior
3. **Legacy deployment** if Flask migration encounters issues

## TODO: Remove After Migration

- [ ] Validate all functionality works in Flask API
- [ ] Confirm all tests pass with new architecture  
- [ ] Verify session management and logging equivalent
- [ ] Remove this file once Flask API is production-ready
- [ ] Remove gradio dependency from requirements.txt

## Documentation

For the new API documentation, see:
- `API_DOCUMENTATION.md` - Complete REST API reference
- `MIGRATION_GUIDE.md` - Migration details and checklist
- `tests/` - Comprehensive test suite for new API

---

**The code below is the original Gradio implementation - DO NOT MODIFY**
**Use the new Flask API for all development and deployment**