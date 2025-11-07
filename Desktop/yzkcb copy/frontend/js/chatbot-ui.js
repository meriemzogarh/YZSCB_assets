// Yazaki Chatbot - UI Controller Module
// Handles all DOM manipulation and user interactions

class ChatbotUI {
    constructor(api) {
        this.api = api;
        this.isOpen = false;
        this.isWaitingForResponse = false;
        this.userInfo = null;
        this.formSubmitted = false;
        
        // DOM Elements
        this.elements = {
            toggle: document.getElementById('chatbot-toggle'),
            container: document.getElementById('chatbot-container'),
            prechatContainer: document.getElementById('prechat-form-container'),
            prechatForm: document.getElementById('prechat-form'),
            chatInterface: document.getElementById('chat-interface'),
            messages: document.getElementById('chat-messages'),
            input: document.getElementById('chat-input'),
            sendBtn: document.getElementById('send-button'),
            closeBtn: document.getElementById('chat-close-btn'),
            resetBtn: document.getElementById('chat-reset-btn'),
            typingIndicator: document.getElementById('typing-indicator'),
            statusIndicator: document.querySelector('.status-indicator'),
            statusText: document.querySelector('.status-text')
        };
        
        this.initEventListeners();
        this.setupSessionCleanup();
        this.checkConnection();
        this.checkExistingUserInfo();
    }
    
    // Check if user info already exists in localStorage
    checkExistingUserInfo() {
        // Always start fresh - clear any existing session data on page load
        this.clearSessionData();
    }

    // Clear all session data to ensure fresh start
    clearSessionData() {
        localStorage.removeItem('yazaki_user_info');
        this.api.resetSession();
        this.userInfo = null;
        this.formSubmitted = false;
    }

    // Setup event listeners to clear session on page leave/refresh
    setupSessionCleanup() {
        // Clear session when page is about to unload (refresh, close tab, navigate away)
        window.addEventListener('beforeunload', () => {
            this.clearSessionData();
        });
        // Use pagehide as a reliable fallback for SPA/navigation in some browsers
        // Do NOT clear on visibilitychange or blur — that would clear sessions when
        // users simply switch windows/tabs. Only clear on unload/pagehide.
        window.addEventListener('pagehide', (event) => {
            // pagehide fires on navigation away or tab close; persisted flag indicates bfcache
            this.clearSessionData();
        });
    }



    // Initialize event listeners
    initEventListeners() {
        // Toggle button click
        this.elements.toggle.addEventListener('click', () => this.toggleChat());
        
        // Close button click
        this.elements.closeBtn.addEventListener('click', () => this.closeChat());
        
        // Reset button click
        this.elements.resetBtn.addEventListener('click', () => this.handleReset());
        
        // Pre-chat form submission
        this.elements.prechatForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Send button click
        this.elements.sendBtn.addEventListener('click', () => this.handleSend());
        
        // Enter key press
        this.elements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });
        
        // Prevent empty messages
        this.elements.input.addEventListener('input', () => {
            const isEmpty = this.elements.input.value.trim() === '';
            this.elements.sendBtn.disabled = isEmpty || this.isWaitingForResponse;
        });
    }
    
    // Handle pre-chat form submission
    async handleFormSubmit(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(this.elements.prechatForm);
        const name = formData.get('name').trim();
        const email = formData.get('email').trim();
        const company = formData.get('company').trim();
        const supplier_type = formData.get('supplier_type');
        const project = formData.get('project').trim();
        const city = formData.get('city').trim();
        const country = formData.get('country').trim();
        const updates = formData.get('updates') === 'on';
        
        // Validate required fields
        let isValid = true;
        
        if (!name) {
            this.showFieldError('name-error');
            isValid = false;
        } else {
            this.hideFieldError('name-error');
        }
        
        if (!email || !this.isValidEmail(email)) {
            this.showFieldError('email-error');
            isValid = false;
        } else {
            this.hideFieldError('email-error');
        }
        
        if (!company) {
            this.showFieldError('company-error');
            isValid = false;
        } else {
            this.hideFieldError('company-error');
        }
        
        if (!supplier_type) {
            this.showFieldError('supplier-error');
            isValid = false;
        } else {
            this.hideFieldError('supplier-error');
        }
        
        if (!city) {
            this.showFieldError('city-error');
            isValid = false;
        } else {
            this.hideFieldError('city-error');
        }
        
        if (!country) {
            this.showFieldError('country-error');
            isValid = false;
        } else {
            this.hideFieldError('country-error');
        }
        
        if (!isValid) {
            return;
        }
        
        // Store user info matching backend expectations
        this.userInfo = {
            full_name: name,
            email: email,
            company_name: company,
            supplier_type: supplier_type,
            project_name: project || 'N/A',
            city: city,
            country: country,
            wants_updates: updates
        };
        
        // Save to localStorage for future sessions
        localStorage.setItem('yazaki_user_info', JSON.stringify(this.userInfo));
        
        // Create a server-side session so backend recognizes this user
        try {
            const result = await this.api.createSession(this.userInfo);
            console.log('Session created on server:', result);

            this.formSubmitted = true;
            this.showChatInterface();
        } catch (err) {
            console.error('Failed to create server session:', err);
            alert('Failed to start session on server. Please check your connection and try again.');
            return;
        }
    }
    
    // Show/hide field errors
    showFieldError(errorId) {
        const errorElement = document.getElementById(errorId);
        if (errorElement) {
            errorElement.classList.add('show');
        }
    }
    
    hideFieldError(errorId) {
        const errorElement = document.getElementById(errorId);
        if (errorElement) {
            errorElement.classList.remove('show');
        }
    }
    
    // Validate email format
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // Show chat interface and hide form
    showChatInterface() {
        this.elements.prechatContainer.classList.add('hidden');
        this.elements.chatInterface.classList.remove('hidden');
        
        // Add personalized welcome message
        if (this.userInfo && this.userInfo.full_name) {
            const welcomeMsg = this.elements.messages.querySelector('.welcome-message');
            if (welcomeMsg) {
                const firstName = this.userInfo.full_name.split(' ')[0];
                welcomeMsg.innerHTML = `
                    <h4>👋 Welcome ${firstName}!</h4>
                    <p>I'm your Yazaki Quality Assistant. Ask me anything about APQP, quality standards, PPAP requirements, and more!</p>
                `;
            }
        }
        
        // Focus input
        setTimeout(() => {
            this.elements.input.focus();
        }, 300);
    }

    // Toggle chat window
    toggleChat() {
        this.isOpen = !this.isOpen;
        this.elements.container.classList.toggle('active', this.isOpen);
        this.elements.toggle.classList.toggle('active', this.isOpen);
        
        if (this.isOpen) {
            if (this.formSubmitted) {
                this.elements.input.focus();
            } else {
                // Focus first form field
                const nameInput = document.getElementById('user-name');
                if (nameInput) {
                    setTimeout(() => nameInput.focus(), 300);
                }
            }
        }
    }

    // Close chat and send summary email
    async closeChat() {
        // Only send email if we have an active session with messages
        if (this.formSubmitted && this.api.sessionId) {
            try {
                console.log('Closing session and sending summary email...');
                await this.sendSessionCloseEmail();
            } catch (error) {
                console.error('Error sending session close email:', error);
                // Continue with closing even if email fails
            }
        }

        // Close the chat window
        this.isOpen = false;
        this.elements.container.classList.remove('active');
        this.elements.toggle.classList.remove('active');
    }

    // Send session closure email
    async sendSessionCloseEmail() {
        if (!this.api.sessionId) {
            console.log('No session ID available for email');
            return;
        }

        try {
            const result = await this.api.closeSession(true);
            console.log('Session closed successfully:', result);
            
            if (result.email_sent) {
                console.log('Summary email sent to admin');
            } else {
                console.log('Session closed but email was not sent');
            }
            
            return result;
        } catch (error) {
            console.error('Error closing session:', error);
            throw error;
        }
    }

    // Check API connection
    async checkConnection() {
        const isConnected = await this.api.checkHealth();
        this.updateConnectionStatus(isConnected);
        
        // Check every 30 seconds
        setTimeout(() => this.checkConnection(), 30000);
    }

    // Update connection status UI
    updateConnectionStatus(isConnected) {
        if (isConnected) {
            this.elements.statusIndicator.classList.remove('disconnected');
            this.elements.statusText.textContent = 'Connected';
        } else {
            this.elements.statusIndicator.classList.add('disconnected');
            this.elements.statusText.textContent = 'Disconnected';
        }
    }

    // Handle send message
    async handleSend() {
        const message = this.elements.input.value.trim();
        
        if (message === '' || this.isWaitingForResponse) {
            return;
        }
        
        // Clear input and disable send
        this.elements.input.value = '';
        this.elements.sendBtn.disabled = true;
        this.isWaitingForResponse = true;
        
        // Add user message to UI
        this.addMessage(message, 'user');
        
        // Show typing indicator (minimal delay)
        this.showTypingIndicator();
        
        try {
            // Send to API with user info
            const response = await this.api.sendMessageWithRetry(message, this.userInfo || {});
            
            // Hide typing indicator immediately
            this.hideTypingIndicator();
            
            // Add bot response directly without delay
            this.addMessage(response.reply, 'bot');
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            
            // Show error message
            this.addMessage(
                'Sorry, I encountered an error processing your message. Please try again.',
                'bot'
            );
        } finally {
            this.isWaitingForResponse = false;
            this.elements.sendBtn.disabled = false;
            this.elements.input.focus();
        }
    }
    
    // Handle reset chat
    handleReset() {
        // Confirm before resetting
        if (confirm('Are you sure you want to reset the conversation? This will clear all messages, log you out, and return to the welcome form.')) {
            this.clearChat();
            this.logoutUser();
        }
    }
    
    // Logout user and show form again
    logoutUser() {
        // Clear user info
        this.userInfo = null;
        this.formSubmitted = false;
        localStorage.removeItem('yazaki_user_info');
        
        // Reset form
        this.elements.prechatForm.reset();
        
        // Hide chat interface and show form
        this.elements.chatInterface.classList.add('hidden');
        this.elements.prechatContainer.classList.remove('hidden');
        
        // Hide all field errors
        this.hideFieldError('name-error');
        this.hideFieldError('email-error');
        this.hideFieldError('company-error');
        this.hideFieldError('supplier-error');
        this.hideFieldError('city-error');
        this.hideFieldError('country-error');
    }

    // Add message to chat
    addMessage(text, type = 'bot') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = type === 'bot' ? 'Y' : 'U';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        // Format text with proper HTML for bot messages
        if (type === 'bot') {
            bubble.innerHTML = this.formatBotMessage(text);
        } else {
            bubble.textContent = text;
        }
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTime(new Date());
        
        contentDiv.appendChild(bubble);
        contentDiv.appendChild(timestamp);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        
        this.elements.messages.appendChild(messageDiv);
        
        // Remove welcome message if exists
        const welcome = this.elements.messages.querySelector('.welcome-message');
        if (welcome) {
            welcome.remove();
        }
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    // Format bot message with proper HTML
    formatBotMessage(text) {
        // Convert markdown-style formatting to HTML
        let formatted = text;
        
        // Bold text: **text** or __text__
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/__(.*?)__/g, '<strong>$1</strong>');
        
        // Lists: lines starting with - or *
        formatted = formatted.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        }
        
        // Numbered lists: lines starting with numbers
        formatted = formatted.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
        if (formatted.match(/^\d+\./m)) {
            formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ol>$1</ol>');
        }
        
        // Line breaks: double newlines become paragraphs
        const paragraphs = formatted.split(/\n\n+/);
        if (paragraphs.length > 1) {
            formatted = paragraphs.map(p => p.trim() ? `<p>${p}</p>` : '').join('');
        } else {
            // Single line breaks
            formatted = formatted.replace(/\n/g, '<br>');
        }
        
        return formatted;
    }

    // Show typing indicator
    showTypingIndicator() {
        this.elements.typingIndicator.classList.remove('hidden');
        this.scrollToBottom();
    }

    // Hide typing indicator
    hideTypingIndicator() {
        this.elements.typingIndicator.classList.add('hidden');
    }

    // Scroll to bottom of messages
    scrollToBottom() {
        setTimeout(() => {
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        }, 50);
    }

    // Format time
    formatTime(date) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    // Clear chat history
    clearChat() {
        const messages = this.elements.messages.querySelectorAll('.message');
        messages.forEach(msg => msg.remove());
        
        // Reset session
        this.api.resetSession();
        
        // Show welcome message
        this.showWelcomeMessage();
    }

    // Show welcome message
    showWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-message';
        welcomeDiv.innerHTML = `
            <h4>👋 Welcome to Yazaki Quality Assistant</h4>
            <p>Ask me anything about APQP, quality standards, PPAP requirements, and more!</p>
        `;
        this.elements.messages.appendChild(welcomeDiv);
    }
}

// Export for use in main script
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatbotUI;
}
