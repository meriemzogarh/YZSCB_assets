// Yazaki Chatbot - API Communication Module
// Handles all backend API communication

class ChatbotAPI {
    constructor(config = API_CONFIG) {
        this.config = config;
        this.baseURL = config.baseURL;
        this.sessionId = this.getOrCreateSessionId();
        this.isConnected = false;
        
        // Chat endpoint for Flask REST API
        this.chatEndpoint = this.config.endpoints.chat;
        this.workingChatEndpoint = null;  // cache working endpoint
    }

    // Create a server-side session (persist registration info)
    async createSession(userInfo = {}) {
        try {
            const payload = { user_info: userInfo };
            const response = await fetch(`${this.baseURL}${this.config.endpoints.sessions}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.session_id) {
                this.sessionId = data.session_id;
                localStorage.setItem(this.config.session.storageKey, this.sessionId);
            }

            return data;
        } catch (error) {
            console.error('Create session failed:', error);
            throw error;
        }
    }

    // Get or create session ID
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem(this.config.session.storageKey);
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem(this.config.session.storageKey, sessionId);
        }
        return sessionId;
    }

    // Check API health
    async checkHealth() {
        try {
            const response = await fetch(
                `${this.baseURL}${this.config.endpoints.health}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                this.isConnected = true;
                return data;
            } else {
                this.isConnected = false;
                return false;
            }
        } catch (error) {
            console.error('Health check failed:', error);
            this.isConnected = false;
            return false;
        }
    }

    // Send message to chat API
    async sendMessage(message, userInfo = {}) {
        if (!message || message.trim() === '') {
            throw new Error('Message cannot be empty');
        }

        try {
            const payload = {
                message: message.trim(),
                session_id: this.sessionId,
                history: [], // Will be managed by frontend
                user_state: {
                    form_completed: true,
                    ...userInfo
                }
            };
            
            console.log('Sending to API:', payload);
            
            const response = await fetch(`${this.baseURL}${this.chatEndpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            
            // Update session ID if provided by backend
            if (data.session_id && data.session_id !== this.sessionId) {
                this.sessionId = data.session_id;
                localStorage.setItem(this.config.session.storageKey, this.sessionId);
            }
            
            return {
                reply: data.reply || data.response || '',
                session_id: data.session_id || this.sessionId,
                sources: data.sources || [],
                metadata: data.metadata || {}
            };
            
        } catch (error) {
            console.error('Send message failed:', error);
            throw error;
        }
    }

    // Retry logic wrapper
    async sendMessageWithRetry(message, userInfo = {}) {
        let lastError;
        
        for (let attempt = 1; attempt <= this.config.retry.maxAttempts; attempt++) {
            try {
                return await this.sendMessage(message, userInfo);
            } catch (error) {
                lastError = error;
                console.warn(`Attempt ${attempt} failed:`, error);
                
                if (attempt < this.config.retry.maxAttempts) {
                    await this.sleep(this.config.retry.delayMs * attempt);
                }
            }
        }
        
        throw lastError;
    }

    // Helper: sleep function
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Get connection status
    getConnectionStatus() {
        return this.isConnected;
    }

    // Reset session
    resetSession() {
        localStorage.removeItem(this.config.session.storageKey);
        this.sessionId = this.getOrCreateSessionId();
    }

    // Close session and send summary email
    async closeSession(sendEmail = true) {
        if (!this.sessionId) {
            throw new Error('No active session to close');
        }

        const response = await fetch(`${this.baseURL}${this.config.endpoints.sessions}/${this.sessionId}/close`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                send_email: sendEmail
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        
        // Clear local session after successful close
        this.resetSession();
        
        return data;
    }
}

// Export for use in main script
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatbotAPI;
}
