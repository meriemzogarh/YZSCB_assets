# Yazaki Chatbot Frontend

A modern, responsive chatbot widget for the Yazaki Quality Assistant system. Provides an intuitive interface for users to interact with the AI-powered quality assistant.

## 📁 Project Structure

```
frontend/
├── index.html              # Main HTML file
├── css/
│   └── chatbot.css        # All styles
├── js/
│   ├── config.js          # Configuration and settings
│   ├── chatbot-api.js     # API communication module
│   ├── chatbot-ui.js      # UI controller module
│   └── chatbot-main.js    # Main application entry point
└── assets/
    └── (images, icons, etc.)
```

## 🚀 Quick Start

### 1. Prerequisites

- A web browser (Chrome, Firefox, Safari, Edge)
- Backend API server running on `http://localhost:7861` (or configured URL)

### 2. Running Locally

Simply open `index.html` in your web browser:

```powershell
# Navigate to frontend directory
cd frontend

# Open in default browser
start index.html

# Or use a local server (recommended)
python -m http.server 8000
# Then visit: http://localhost:8000
```

### 3. Configuration

Edit `js/config.js` to configure:

```javascript
const API_CONFIG = {
    baseURL: 'http://localhost:5001',  // Your backend API URL
    timeout: 30000,                     // Request timeout
    // ... other settings
};
```

## 🎨 Features

- **Modern UI**: Clean, professional design with Yazaki branding
- **Real-time Status**: Connection indicator shows API availability
- **Responsive**: Works on desktop, tablet, and mobile devices
- **Session Persistence**: Maintains conversation history across page refreshes
- **Typing Indicators**: Shows when bot is processing
- **Error Handling**: Graceful handling of network errors
- **Accessibility**: ARIA labels and keyboard navigation support

## 🔧 Customization

### Branding Colors

Edit `css/chatbot.css`:

```css
/* Primary brand color */
#DC0032  /* Yazaki Red */

/* Secondary colors */
#1a1a1a  /* Dark Gray */
#A00028  /* Darker Red */
```

### API Configuration

Edit `js/config.js`:

```javascript
// Change API endpoint
API_CONFIG.baseURL = 'https://your-api-domain.com';

// Adjust timeouts
API_CONFIG.timeout = 60000;  // 60 seconds

// Modify retry behavior
API_CONFIG.retry.maxAttempts = 5;
```

### UI Behavior

Edit `js/config.js`:

```javascript
// Adjust typing delay
API_CONFIG.ui.typingDelayMs = 2000;

// Change auto-scroll delay
API_CONFIG.ui.autoScrollDelay = 200;
```

## 📦 Deployment

### Option 1: Static File Hosting

Upload all files to any static hosting service:

- **GitHub Pages**: Push to `gh-pages` branch
- **Netlify**: Drag & drop `frontend/` folder
- **Vercel**: Connect repository and deploy
- **AWS S3**: Upload to S3 bucket with static hosting enabled

### Option 2: CDN Deployment

For production, consider using a CDN:

1. Upload files to CDN
2. Update `config.js` with production API URL
3. Enable CORS on backend API
4. Configure CSP headers

### Option 3: Server Integration

Serve frontend from backend (Flask example):

```python
from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='frontend')

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')
```

## 🔒 Security Considerations

1. **HTTPS**: Always use HTTPS in production
2. **CORS**: Configure proper CORS headers on backend
3. **CSP**: Implement Content Security Policy
4. **Input Validation**: Backend validates all inputs
5. **Rate Limiting**: Backend implements rate limiting

## 🧪 Testing

### Manual Testing

1. Open `index.html` in browser
2. Click chatbot toggle button (bottom-right)
3. Check connection status (top-right)
4. Send test messages:
   - "What is APQP?"
   - "Explain PPAP phases"
   - "Quality standards overview"

### Browser Console Testing

```javascript
// Access chatbot instance
window.yazakiChatbot.api.checkHealth()
  .then(status => console.log('API Status:', status));

// Send test message
window.yazakiChatbot.api.sendMessage('Test message')
  .then(response => console.log('Response:', response));

// Clear chat history
window.yazakiChatbot.ui.clearChat();
```

### Cross-Browser Testing

Test on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 🐛 Troubleshooting

### Chat Widget Not Appearing

1. Check browser console for JavaScript errors
2. Verify all JS files are loaded correctly
3. Ensure CSS file is linked properly

### Connection Status Shows "Disconnected"

1. Verify backend API is running
2. Check `config.js` has correct API URL
3. Test API directly: `http://localhost:5001/api/health`
4. Check browser console for CORS errors

### Messages Not Sending

1. Open browser console and check for errors
2. Verify network requests in DevTools Network tab
3. Check backend logs for errors
4. Verify session storage is working

### Styling Issues

1. Clear browser cache
2. Check if CSS file is loading (Network tab)
3. Verify no CSS conflicts from parent page
4. Check browser compatibility

## 📖 Module Documentation

### config.js

Central configuration for API endpoints, timeouts, and UI settings.

**Key Settings:**
- `baseURL`: Backend API base URL
- `endpoints`: API endpoint paths
- `timeout`: Request timeout in milliseconds
- `session.storageKey`: localStorage key for session ID

### chatbot-api.js

Handles all backend API communication.

**Key Methods:**
- `checkHealth()`: Check API availability
- `sendMessage(message, userInfo)`: Send chat message
- `sendMessageWithRetry(message, userInfo)`: Send with retry logic
- `resetSession()`: Clear session and create new ID

### chatbot-ui.js

Manages DOM manipulation and user interactions.

**Key Methods:**
- `toggleChat()`: Open/close chat window
- `addMessage(text, type)`: Add message to chat
- `showTypingIndicator()`: Show bot typing animation
- `clearChat()`: Clear all messages and reset

### chatbot-main.js

Application entry point that initializes API and UI.

**Global Object:**
```javascript
window.yazakiChatbot = {
    api: ChatbotAPI,    // API instance
    ui: ChatbotUI,      // UI instance
    version: '1.0.0'    // Version number
}
```

## 🔄 Updates and Maintenance

### Updating Configuration

1. Edit `js/config.js`
2. No rebuild needed - just refresh browser

### Updating Styles

1. Edit `css/chatbot.css`
2. Clear browser cache
3. Refresh page

### Updating Logic

1. Edit relevant JS module
2. Test in browser console
3. Verify no console errors
4. Test all functionality

## 📞 Support

For issues or questions:

1. Check browser console for errors
2. Review backend logs
3. Consult main project documentation
4. Check TROUBLESHOOTING_405.md

## 📄 License

Part of the Yazaki Chatbot System.

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Maintained By**: Yazaki Development Team
