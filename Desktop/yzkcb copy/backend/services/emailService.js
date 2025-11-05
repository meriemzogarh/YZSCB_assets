/**
 * Email Service
 * 
 * Handles email notifications for session summaries
 */

const nodemailer = require('nodemailer');
const Session = require('../models/Session');

/**
 * Create nodemailer transporter with SMTP configuration
 * @returns {nodemailer.Transporter}
 */
const createTransporter = () => {
  const config = {
    host: process.env.MAIL_HOST || 'smtp.gmail.com',
    port: parseInt(process.env.MAIL_PORT) || 587,
    secure: process.env.MAIL_SECURE === 'true', // true for 465, false for other ports
    auth: {
      user: process.env.MAIL_USER,
      pass: process.env.MAIL_PASS
    }
  };

  // Validate configuration
  if (!config.auth.user || !config.auth.pass) {
    throw new Error('Email configuration is missing. Please check MAIL_USER and MAIL_PASS in .env file.');
  }

  return nodemailer.createTransport(config);
};

/**
 * Fetch session data from MongoDB
 * @param {string} sessionId - UUID of the session
 * @returns {Promise<Object>} Session document with all data
 * @throws {Error} If session not found
 */
const fetchSessionData = async (sessionId) => {
  try {
    const session = await Session.findOne({ sessionId }).lean();
    
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    return session;
  } catch (error) {
    console.error(`Error fetching session data for ${sessionId}:`, error.message);
    throw error;
  }
};

/**
 * Calculate session duration in human-readable format
 * @param {Date} startTime - Session start timestamp
 * @param {Date} endTime - Session end timestamp
 * @returns {string} Formatted duration (e.g., "33 minutes", "1 hour 15 minutes")
 */
const calculateDuration = (startTime, endTime) => {
  const durationMs = new Date(endTime) - new Date(startTime);
  const durationMinutes = Math.floor(durationMs / 60000);
  
  if (durationMinutes < 60) {
    return `${durationMinutes} minute${durationMinutes !== 1 ? 's' : ''}`;
  }
  
  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;
  
  if (minutes === 0) {
    return `${hours} hour${hours !== 1 ? 's' : ''}`;
  }
  
  return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} minute${minutes !== 1 ? 's' : ''}`;
};

/**
 * Format timestamp for display
 * @param {Date} timestamp - Date to format
 * @returns {string} Formatted date string (e.g., "2025-10-20 10:15")
 */
const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

/**
 * Build plain text email summary
 * @param {Object} session - Session document from MongoDB
 * @returns {string} Formatted plain text summary
 */
const buildPlainTextSummary = (session) => {
  const { sessionId, userInfo, messages, createdAt, updatedAt, status } = session;
  
  // Determine end time based on status
  const endTime = status === 'ended' || status === 'expired' ? updatedAt : new Date();
  const duration = calculateDuration(createdAt, endTime);
  
  // Build header
  let summary = '🧾 CHAT SUMMARY\n';
  summary += '═══════════════════════════════════════\n\n';
  
  // Session info
  summary += '📋 Session Information:\n';
  summary += `Session ID: ${sessionId}\n`;
  summary += `Start: ${formatTimestamp(createdAt)}\n`;
  summary += `End: ${formatTimestamp(endTime)}\n`;
  summary += `Duration: ${duration}\n`;
  summary += `Status: ${status.toUpperCase()}\n`;
  summary += `Total Messages: ${messages.length}\n\n`;
  
  // User info
  summary += '👤 User Information:\n';
  summary += `Name: ${userInfo.fullName}\n`;
  summary += `Email: ${userInfo.email}\n`;
  summary += `Company: ${userInfo.companyName}\n`;
  summary += `Supplier Type: ${userInfo.supplierType}\n\n`;
  
  // Conversation transcript
  summary += '💬 Conversation Transcript:\n';
  summary += '───────────────────────────────────────\n\n';
  
  if (messages.length === 0) {
    summary += '(No messages in this session)\n\n';
  } else {
    messages.forEach((msg, index) => {
      const speaker = msg.sender === 'user' ? 'User' : 'Bot';
      const time = formatTimestamp(msg.timestamp);
      
      summary += `[${time}] ${speaker}:\n`;
      summary += `${msg.text}\n\n`;
      
      // Add metadata if available (for bot messages)
      if (msg.metadata && Object.keys(msg.metadata).length > 0) {
        summary += `   ℹ️ Metadata: ${JSON.stringify(msg.metadata, null, 2)}\n\n`;
      }
    });
  }
  
  summary += '═══════════════════════════════════════\n';
  summary += `Generated on: ${formatTimestamp(new Date())}\n`;
  
  return summary;
};

/**
 * Build HTML email summary with better formatting
 * @param {Object} session - Session document from MongoDB
 * @returns {string} Formatted HTML summary
 */
const buildHtmlSummary = (session) => {
  const { sessionId, userInfo, messages, createdAt, updatedAt, status } = session;
  
  // Determine end time based on status
  const endTime = status === 'ended' || status === 'expired' ? updatedAt : new Date();
  const duration = calculateDuration(createdAt, endTime);
  
  let html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chat Summary - ${sessionId}</title>
  <style>
    /* Compact email styles: smaller paddings, tighter spacing */
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.4;
      color: #333;
      max-width: 680px;
      margin: 0 auto;
      padding: 12px;
      background-color: #f7f7f7;
      font-size: 13px;
    }
    .container {
      background-color: #ffffff;
      border-radius: 6px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      padding: 12px;
    }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 10px;
      border-radius: 6px 6px 0 0;
      margin: -12px -12px 12px -12px;
    }
    .header h1 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    .section {
      margin-bottom: 12px;
      padding: 10px;
      background-color: #fafafa;
      border-radius: 4px;
      border-left: 4px solid #667eea;
    }
    .section-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 8px;
      color: #667eea;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .info-grid {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 6px;
      align-items: center;
    }
    .info-label {
      font-weight: 600;
      color: #666;
      font-size: 13px;
    }
    .info-value {
      color: #333;
      font-size: 13px;
    }
    .message {
      margin-bottom: 10px;
      padding: 8px;
      border-radius: 6px;
      background-color: #ffffff;
      border: 1px solid #e9e9e9;
      font-size: 13px;
    }
    .message-user { border-left: 4px solid #4CAF50; }
    .message-bot { border-left: 4px solid #2196F3; }
    .message-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      font-size: 11px;
      color: #666;
    }
    .message-sender { font-weight: 600; font-size: 13px; }
    .message-sender-user { color: #4CAF50; }
    .message-sender-bot { color: #2196F3; }
    .message-text { color: #333; white-space: pre-wrap; word-wrap: break-word; font-size: 13px; }
    .metadata {
      margin-top: 8px;
      padding: 8px;
      background-color: #f3f3f3;
      border-radius: 4px;
      font-size: 11px;
      color: #666;
      font-family: monospace;
      max-height: 120px;
      overflow: auto;
    }
    .footer {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #eaeaea;
      text-align: center;
      color: #666;
      font-size: 12px;
    }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
    .badge-active { background-color: #4CAF50; color: white; }
    .badge-ended { background-color: #9E9E9E; color: white; }
    .badge-expired { background-color: #F44336; color: white; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🧾 Chat Session Summary</h1>
    </div>
    
    <div class="section">
      <div class="section-title">📋 Session Information</div>
      <div class="info-grid">
        <div class="info-label">Session ID:</div>
        <div class="info-value"><code>${sessionId}</code></div>
        
        <div class="info-label">Start Time:</div>
        <div class="info-value">${formatTimestamp(createdAt)}</div>
        
        <div class="info-label">End Time:</div>
        <div class="info-value">${formatTimestamp(endTime)}</div>
        
        <div class="info-label">Duration:</div>
        <div class="info-value">${duration}</div>
        
        <div class="info-label">Status:</div>
        <div class="info-value">
          <span class="badge badge-${status}">${status.toUpperCase()}</span>
        </div>
        
        <div class="info-label">Total Messages:</div>
        <div class="info-value">${messages.length}</div>
      </div>
    </div>
    
    <div class="section">
      <div class="section-title">👤 User Information</div>
      <div class="info-grid">
        <div class="info-label">Name:</div>
        <div class="info-value">${userInfo.fullName}</div>
        
        <div class="info-label">Email:</div>
        <div class="info-value"><a href="mailto:${userInfo.email}">${userInfo.email}</a></div>
        
        <div class="info-label">Company:</div>
        <div class="info-value">${userInfo.companyName}</div>
        
        <div class="info-label">Supplier Type:</div>
        <div class="info-value">${userInfo.supplierType}</div>
      </div>
    </div>
    
    <div class="section">
      <div class="section-title">💬 Conversation Transcript</div>
  `;
  
  if (messages.length === 0) {
    html += '<p style="color: #666; font-style: italic;">(No messages in this session)</p>';
  } else {
    messages.forEach((msg) => {
      const senderClass = msg.sender === 'user' ? 'user' : 'bot';
      const senderLabel = msg.sender === 'user' ? 'User' : 'Bot';
      const time = formatTimestamp(msg.timestamp);
      
      html += `
      <div class="message message-${senderClass}">
        <div class="message-header">
          <span class="message-sender message-sender-${senderClass}">${senderLabel}</span>
          <span class="message-time">${time}</span>
        </div>
        <div class="message-text">${escapeHtml(msg.text)}</div>
      `;
      
      if (msg.metadata && Object.keys(msg.metadata).length > 0) {
        html += `
        <div class="metadata">
          <strong>Metadata:</strong> ${escapeHtml(JSON.stringify(msg.metadata, null, 2))}
        </div>
        `;
      }
      
      html += '</div>';
    });
  }
  
  html += `
    </div>
    
    <div class="footer">
      <p>Generated on ${formatTimestamp(new Date())}</p>
      <p>Yazaki Chatbot System | Session Management</p>
    </div>
  </div>
</body>
</html>
  `;
  
  return html;
};

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
};

/**
 * Send email with session summary
 * @param {string} toEmail - Recipient email address
 * @param {string} subject - Email subject
 * @param {string} textContent - Plain text content
 * @param {string} htmlContent - HTML content
 * @returns {Promise<Object>} Nodemailer send result
 */
const sendEmail = async (toEmail, subject, textContent, htmlContent) => {
  try {
    const transporter = createTransporter();
    
    const mailOptions = {
      from: process.env.MAIL_FROM || `"Yazaki Chatbot" <${process.env.MAIL_USER}>`,
      to: toEmail,
      subject: subject,
      text: textContent,
      html: htmlContent
    };
    
    const info = await transporter.sendMail(mailOptions);
    
    console.log(`✅ Email sent successfully to ${toEmail}`);
    console.log(`Message ID: ${info.messageId}`);
    
    return {
      success: true,
      messageId: info.messageId,
      recipient: toEmail
    };
  } catch (error) {
    console.error(`❌ Error sending email to ${toEmail}:`, error.message);
    throw error;
  }
};

/**
 * Main function: Send summary email for a chat session
 * 
 * @param {string} sessionId - UUID of the session to summarize
 * @returns {Promise<Object>} Result object with success status and details
 * 
 * @example
 * const result = await sendSummaryEmail('550e8400-e29b-41d4-a716-446655440000');
 * console.log(result.message); // "Email sent successfully to admin@example.com"
 */
const sendSummaryEmail = async (sessionId) => {
  console.log(`📧 Starting email summary process for session: ${sessionId}`);
  
  try {
    // Step 1: Validate admin email configuration
    const adminEmail = process.env.ADMIN_EMAIL;
    if (!adminEmail) {
      throw new Error('ADMIN_EMAIL not configured in .env file');
    }
    
    // Step 2: Fetch session data from MongoDB
    console.log(`📥 Fetching session data from MongoDB...`);
    const session = await fetchSessionData(sessionId);
    console.log(`✓ Session data retrieved: ${session.messages.length} messages`);
    
    // Step 3: Build email content
    console.log(`📝 Building email summary...`);
    const plainTextSummary = buildPlainTextSummary(session);
    const htmlSummary = buildHtmlSummary(session);
    console.log(`✓ Email content generated`);
    
    // Step 4: Prepare email subject
    const subject = `Chat Summary - ${session.userInfo.fullName} (${session.userInfo.companyName}) - Session ${sessionId.substring(0, 8)}`;
    
    // Step 5: Send email
    console.log(`📮 Sending email to ${adminEmail}...`);
    const result = await sendEmail(adminEmail, subject, plainTextSummary, htmlSummary);
    
    // Step 6: Return success confirmation
    const confirmation = {
      success: true,
      message: `Email sent successfully to ${adminEmail}`,
      sessionId: sessionId,
      messageId: result.messageId,
      timestamp: new Date().toISOString(),
      details: {
        recipient: adminEmail,
        messageCount: session.messages.length,
        userEmail: session.userInfo.email,
        userName: session.userInfo.fullName
      }
    };
    
    console.log(`✅ Email summary process completed successfully`);
    return confirmation;
    
  } catch (error) {
    console.error(`❌ Failed to send summary email for session ${sessionId}:`, error);
    
    // Return error details
    return {
      success: false,
      message: `Failed to send email: ${error.message}`,
      sessionId: sessionId,
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
};

// Export all functions
module.exports = {
  sendSummaryEmail,
  fetchSessionData,
  buildPlainTextSummary,
  buildHtmlSummary,
  sendEmail,
  createTransporter,
  calculateDuration,
  formatTimestamp
};
