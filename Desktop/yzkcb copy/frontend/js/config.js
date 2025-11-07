// Yazaki Chatbot - Configuration
// Central configuration file for API endpoints and settings

const API_CONFIG = {
    // API Base URL - change for different environments
    baseURL: 'http://localhost:8000',
    
    // API Endpoints for Flask REST API backend
    endpoints: {
        chat: '/api/chat',
        sessions: '/api/sessions',
        stream: '/api/stream', 
        health: '/api/health',
        models: '/api/models',
        init: '/api/init'
    },
    
    // Request timeout in milliseconds
    timeout: 30000,
    
    // Retry configuration
    retry: {
        maxAttempts: 3,
        delayMs: 1000
    },
    
    // Session configuration
    session: {
        storageKey: 'yazaki_chatbot_session_id',
        expiryDays: 30
    },
    
    // UI Configuration
    ui: {
        typingDelayMs: 1500,
        autoScrollDelay: 100
    }
};

// Environment-specific overrides (can be set via build process)
if (typeof window !== 'undefined' && window.CHATBOT_ENV === 'production') {
    API_CONFIG.baseURL = 'http://localhost:7861';
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}
