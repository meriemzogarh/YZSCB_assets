// Yazaki Chatbot - Main Application Entry Point
// Initializes and coordinates API and UI components

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatbot);
    } else {
        initChatbot();
    }
    
    function initChatbot() {
        console.log('Initializing Yazaki Chatbot...');
        
        try {
            // Initialize API client
            const api = new ChatbotAPI(API_CONFIG);
            console.log('API client initialized');
            
            // Initialize UI controller
            const ui = new ChatbotUI(api);
            console.log('UI controller initialized');
            
            // Make instances available globally for debugging (optional)
            window.yazakiChatbot = {
                api: api,
                ui: ui,
                version: '1.0.0'
            };
            
            console.log('Yazaki Chatbot ready!');
            
        } catch (error) {
            console.error('Failed to initialize chatbot:', error);
            alert('Failed to initialize chatbot. Please refresh the page.');
        }
    }
})();
