/**
 * Chat interface JavaScript for Yazaki Chatbot
 * Handles API communication, message rendering, and UI interactions
 */

class YazakiChatbot {
    constructor() {
        this.sessionId = null;
        this.chatHistory = [];
        this.isInitialized = false;
        this.isRegistered = false;
        this.userState = {};
        this.apiBaseUrl = window.location.origin;
        
        this.initializeElements();
        this.attachEventListeners();
        this.checkSystemStatus();
        this.loadModels();
        this.updateUIState();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendBtn = document.getElementById('sendBtn');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        // Status elements
        this.apiStatus = document.getElementById('apiStatus');
        this.apiStatusText = document.getElementById('apiStatusText');
        this.dbStatus = document.getElementById('dbStatus');
        this.dbStatusText = document.getElementById('dbStatusText');
        this.sessionIdEl = document.getElementById('sessionId');
        this.currentModelEl = document.getElementById('currentModel');
        this.initBtn = document.getElementById('initBtn');
        
        // Registration elements
        this.registrationPanel = document.getElementById('registrationPanel');
        this.sessionPanel = document.getElementById('sessionPanel');
        this.registrationForm = document.getElementById('registrationForm');
        this.logoutBtn = document.getElementById('logoutBtn');
        this.registeredUserEl = document.getElementById('registeredUser');
    }

    attachEventListeners() {
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit(e);
            }
        });
        
        // Registration form
        this.registrationForm.addEventListener('submit', (e) => this.handleRegistration(e));
        this.logoutBtn.addEventListener('click', () => this.logout());
    }

    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/health`);
            const data = await response.json();
            
            this.updateStatusIndicators(data);
            
            if (data.status === 'healthy') {
                this.isInitialized = true;
                this.updateApiStatus('connected', 'System ready');
            } else {
                this.updateApiStatus('disconnected', 'System needs initialization');
            }
        } catch (error) {
            console.error('Health check failed:', error);
            this.updateApiStatus('disconnected', 'Connection failed');
        }
    }

    async loadModels() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/models`);
            const data = await response.json();
            
            if (data.current && data.current !== 'unknown') {
                this.currentModelEl.textContent = data.current;
            } else {
                this.currentModelEl.textContent = 'Not configured';
            }
        } catch (error) {
            console.error('Failed to load models:', error);
            this.currentModelEl.textContent = 'Error loading';
        }
    }

    updateStatusIndicators(healthData) {
        const { details } = healthData;
        
        // Update API status
        if (details.overall === 'healthy') {
            this.updateApiStatus('connected', 'API connected');
        } else if (details.overall === 'partially_healthy') {
            this.updateApiStatus('loading', 'Partially ready');
        } else {
            this.updateApiStatus('disconnected', 'API unavailable');
        }

        // Update database status
        if (details.mongodb?.status === 'connected') {
            this.updateDbStatus('connected', 'Database ready');
        } else {
            this.updateDbStatus('disconnected', 'Database unavailable');
        }

        // Update vector store status in API status if available
        if (details.vector_store?.status === 'initialized') {
            this.updateApiStatus('connected', 'System ready');
        }
    }

    updateApiStatus(status, text) {
        this.apiStatus.className = `status-dot ${status}`;
        this.apiStatusText.textContent = text;
    }

    updateDbStatus(status, text) {
        this.dbStatus.className = `status-dot ${status}`;
        this.dbStatusText.textContent = text;
    }

    async initializeSystem() {
        this.initBtn.disabled = true;
        this.initBtn.textContent = 'Initializing...';
        this.updateApiStatus('loading', 'Initializing system...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/init`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    vector_store_name: 'vector_store_json'
                })
            });

            const data = await response.json();

            if (response.ok && (data.status === 'ok' || data.status === 'partial')) {
                this.isInitialized = true;
                this.updateApiStatus('connected', 'System initialized');
                const message = this.isRegistered ? 
                    '✅ System initialized successfully! You can now start chatting.' :
                    '✅ System initialized successfully! Please complete registration to start chatting.';
                this.addSystemMessage(message);
                
                // Update UI state
                this.updateUIState();
                
                // Refresh health status
                setTimeout(() => this.checkSystemStatus(), 1000);
            } else {
                this.updateApiStatus('disconnected', 'Initialization failed');
                this.addErrorMessage(`Initialization failed: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Initialization failed:', error);
            this.updateApiStatus('disconnected', 'Initialization error');
            this.addErrorMessage('Failed to initialize system. Please check the console for details.');
        } finally {
            this.initBtn.disabled = false;
            this.initBtn.textContent = 'Initialize System';
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput.value.trim();
        if (!message) return;

        if (!this.isInitialized) {
            this.addErrorMessage('System not initialized. Please click "Initialize System" first.');
            return;
        }

        if (!this.isRegistered) {
            this.addErrorMessage('Please complete registration first.');
            return;
        }

        // Add user message to chat
        this.addUserMessage(message);
        this.messageInput.value = '';
        this.setInputDisabled(true);

        try {
            // Prepare request payload
            const payload = {
                message: message,
                history: this.chatHistory,
                session_id: this.sessionId,
                user_state: this.userState
            };

            // Show typing indicator
            this.showTyping(true);

            // Make API request
            const response = await fetch(`${this.apiBaseUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                // Update session ID if provided
                if (data.session_id && !this.sessionId) {
                    this.sessionId = data.session_id;
                    this.sessionIdEl.textContent = this.sessionId.substring(0, 8) + '...';
                }

                // Add assistant response
                this.addAssistantMessage(data.reply, data.metadata);

                // Update chat history
                this.chatHistory.push(
                    { role: 'user', content: message },
                    { role: 'assistant', content: data.reply }
                );
            } else {
                this.addErrorMessage(data.error || 'Failed to get response from server');
            }
        } catch (error) {
            console.error('Chat request failed:', error);
            this.addErrorMessage('Network error occurred. Please try again.');
        } finally {
            this.showTyping(false);
            this.setInputDisabled(false);
            this.messageInput.focus();
        }
    }

    addUserMessage(message) {
        const messageEl = this.createMessageElement('user-message', message);
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    addAssistantMessage(message, metadata = {}) {
        const messageEl = this.createMessageElement('assistant-message', message, metadata);
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    addSystemMessage(message) {
        const messageEl = this.createMessageElement('assistant-message', message);
        messageEl.querySelector('.message-time').textContent = 'System';
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    addErrorMessage(message) {
        const errorEl = document.createElement('div');
        errorEl.className = 'error-message';
        errorEl.textContent = message;
        this.chatMessages.appendChild(errorEl);
        this.scrollToBottom();
    }

    createMessageElement(className, content, metadata = {}) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${className}`;
        
        const contentEl = document.createElement('div');
        contentEl.innerHTML = this.formatMessage(content);
        
        const timeEl = document.createElement('div');
        timeEl.className = 'message-time';
        timeEl.textContent = metadata.timestamp || new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageEl.appendChild(contentEl);
        messageEl.appendChild(timeEl);
        
        return messageEl;
    }

    formatMessage(content) {
        // Convert markdown-like formatting to HTML
        return content
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
            .replace(/📋 \*\*Referenced Documents:\*\*/g, '<br><strong>📋 Referenced Documents:</strong>')
            .replace(/  • ([^\n]+)/g, '<br>&nbsp;&nbsp;• $1');
    }

    async handleRegistration(e) {
        e.preventDefault();
        
        const formData = new FormData(this.registrationForm);
        const name = formData.get('userName').trim();
        const company = formData.get('userCompany').trim();
        const role = formData.get('userRole');

        if (!name || !company || !role) {
            this.addErrorMessage('Please fill in all registration fields.');
            return;
        }

        try {
            // Set up user state
            this.userState = {
                form_completed: true,
                user_name: name,
                company: company,
                role: role,
                registration_time: new Date().toISOString()
            };

            // Generate new session ID for this registration
            this.sessionId = null;
            this.isRegistered = true;

            // Update UI
            this.showRegistrationSuccess(name, company);
            this.addSystemMessage(`Welcome ${name} from ${company}! Your session has been started. You can now ask questions about Yazaki supplier quality requirements.`);

        } catch (error) {
            console.error('Registration error:', error);
            this.addErrorMessage('Registration failed. Please try again.');
        }
    }

    showRegistrationSuccess(name, company) {
        // Hide registration form, show session info
        this.registrationPanel.style.display = 'none';
        this.sessionPanel.style.display = 'block';
        
        // Update session info
        this.registeredUserEl.textContent = `${name} (${company})`;
        
        // Enable chat if system is initialized
        this.updateUIState();
    }

    logout() {
        // Reset session
        this.sessionId = null;
        this.isRegistered = false;
        this.userState = {};
        this.chatHistory = [];

        // Clear chat
        this.chatMessages.innerHTML = '';

        // Reset UI
        this.registrationPanel.style.display = 'block';
        this.sessionPanel.style.display = 'none';
        this.sessionIdEl.textContent = 'Not started';
        
        // Reset form
        this.registrationForm.reset();

        this.addSystemMessage('Session ended. Please register again to start a new session.');
    }

    showTyping(show) {
        this.typingIndicator.style.display = show ? 'block' : 'none';
        if (show) {
            this.scrollToBottom();
        }
    }

    setInputDisabled(disabled) {
        this.messageInput.disabled = disabled;
        this.sendBtn.disabled = disabled;
        this.sendBtn.textContent = disabled ? 'Processing...' : 'Send';
    }

    updateUIState() {
        // Initially disable chat and show registration
        this.setInputDisabled(true);
        
        if (!this.isRegistered) {
            this.messageInput.placeholder = 'Complete registration first to start chatting...';
            this.registrationPanel.style.display = 'block';
            this.sessionPanel.style.display = 'none';
        } else {
            this.messageInput.placeholder = 'Ask about supplier quality, PPAP, APQP...';
            this.registrationPanel.style.display = 'none';
            this.sessionPanel.style.display = 'block';
            this.setInputDisabled(!this.isInitialized);
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    // Streaming chat method (optional enhancement)
    async handleStreamingChat(message) {
        if (!this.isInitialized) {
            this.addErrorMessage('System not initialized. Please click "Initialize System" first.');
            return;
        }

        this.addUserMessage(message);
        this.messageInput.value = '';
        this.setInputDisabled(true);
        this.showTyping(true);

        try {
            const payload = {
                message: message,
                history: this.chatHistory,
                session_id: this.sessionId,
                user_state: { form_completed: true }
            };

            const response = await fetch(`${this.apiBaseUrl}/api/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let accumulatedResponse = '';
            let messageElement = null;

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        
                        if (dataStr === '[DONE]') {
                            this.showTyping(false);
                            return;
                        }

                        try {
                            const data = JSON.parse(dataStr);

                            if (data.error) {
                                this.addErrorMessage(data.error);
                                return;
                            }

                            if (data.session_id && !this.sessionId) {
                                this.sessionId = data.session_id;
                                this.sessionIdEl.textContent = this.sessionId.substring(0, 8) + '...';
                            }

                            if (data.chunk && !messageElement) {
                                // Create initial message element
                                messageElement = this.createMessageElement('assistant-message', '');
                                this.chatMessages.appendChild(messageElement);
                                this.showTyping(false);
                            }

                            if (data.accumulated) {
                                accumulatedResponse = data.accumulated;
                                if (messageElement) {
                                    messageElement.querySelector('div').innerHTML = this.formatMessage(accumulatedResponse);
                                    this.scrollToBottom();
                                }
                            }

                            if (data.done) {
                                // Update chat history
                                this.chatHistory.push(
                                    { role: 'user', content: message },
                                    { role: 'assistant', content: accumulatedResponse }
                                );
                                return;
                            }
                        } catch (parseError) {
                            console.error('Failed to parse streaming data:', parseError);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Streaming chat failed:', error);
            this.addErrorMessage('Network error occurred during streaming. Please try again.');
        } finally {
            this.showTyping(false);
            this.setInputDisabled(false);
            this.messageInput.focus();
        }
    }
}

// Global functions for HTML event handlers
function initializeSystem() {
    if (window.chatbot) {
        window.chatbot.initializeSystem();
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new YazakiChatbot();
});

// Add some utility functions
window.clearChat = function() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="assistant-message message">
            <div>Welcome to the Yazaki Supplier Quality Assistant! I'm here to help you with automotive quality processes, supplier requirements, PPAP, APQP, and quality documentation.</div>
            <div class="message-time">System</div>
        </div>
    `;
    if (window.chatbot) {
        window.chatbot.chatHistory = [];
    }
};

window.exportChat = function() {
    if (window.chatbot && window.chatbot.chatHistory.length > 0) {
        const chatData = {
            session_id: window.chatbot.sessionId,
            timestamp: new Date().toISOString(),
            history: window.chatbot.chatHistory
        };
        
        const blob = new Blob([JSON.stringify(chatData, null, 2)], { 
            type: 'application/json' 
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `yazaki-chat-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};