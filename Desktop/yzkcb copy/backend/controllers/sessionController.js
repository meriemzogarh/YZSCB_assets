/**
 * Session Controller
 * 
 * Handles all session-related operations including message storage
 */

const Session = require('../models/Session');
const { v4: uuidv4 } = require('uuid');

/**
 * Create a new chat session
 * @route POST /api/sessions
 */
const createSession = async (req, res) => {
  try {
    const { userInfo } = req.body;

    // Validate required fields
    if (!userInfo || !userInfo.fullName || !userInfo.email || !userInfo.companyName || !userInfo.supplierType) {
      return res.status(400).json({
        success: false,
        error: 'Missing required user information fields'
      });
    }

    // Generate unique session ID
    const sessionId = uuidv4();

    // Create new session
    const session = new Session({
      sessionId,
      userInfo: {
        fullName: userInfo.fullName,
        email: userInfo.email,
        companyName: userInfo.companyName,
        projectName: userInfo.projectName || 'N/A',
        supplierType: userInfo.supplierType,
        location: {
          city: userInfo.city,
          country: userInfo.country
        }
      },
      messages: [],
      status: 'active'
    });

    await session.save();

    console.log(`📝 Session created: ${sessionId.substring(0, 8)}...`);

    res.status(201).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        userInfo: session.userInfo,
        status: session.status,
        createdAt: session.createdAt
      }
    });

  } catch (error) {
    console.error('❌ Error creating session:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create session',
      message: error.message
    });
  }
};

/**
 * Add a user message to session and update activity
 * @route POST /api/sessions/:sessionId/messages/user
 */
const addUserMessage = async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { text } = req.body;

    // Validate input
    if (!text || text.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Message text is required'
      });
    }

    // Find session
    const session = await Session.findOne({ sessionId, status: 'active' });

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Active session not found'
      });
    }

    // Add user message
    await session.addMessage('user', text.trim());

    console.log(`💬 User message added to session ${sessionId.substring(0, 8)}...`);

    res.status(200).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        messageCount: session.messageCount,
        lastActivity: session.lastActivity,
        messages: session.messages
      }
    });

  } catch (error) {
    console.error('❌ Error adding user message:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to add user message',
      message: error.message
    });
  }
};

/**
 * Add a bot message to session
 * @route POST /api/sessions/:sessionId/messages/bot
 */
const addBotMessage = async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { text, metadata } = req.body;

    // Validate input
    if (!text || text.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Message text is required'
      });
    }

    // Find session
    const session = await Session.findOne({ sessionId, status: 'active' });

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Active session not found'
      });
    }

    // Add bot message with optional metadata
    await session.addMessage('bot', text.trim(), metadata || {});

    console.log(`🤖 Bot message added to session ${sessionId.substring(0, 8)}...`);

    res.status(200).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        messageCount: session.messageCount,
        lastActivity: session.lastActivity,
        messages: session.messages
      }
    });

  } catch (error) {
    console.error('❌ Error adding bot message:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to add bot message',
      message: error.message
    });
  }
};

/**
 * Complete chat interaction (user + bot messages in one call)
 * @route POST /api/sessions/:sessionId/chat
 */
const addChatInteraction = async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { userMessage, botMessage, metadata } = req.body;

    // Validate input
    if (!userMessage || !botMessage) {
      return res.status(400).json({
        success: false,
        error: 'Both userMessage and botMessage are required'
      });
    }

    // Find session
    const session = await Session.findOne({ sessionId, status: 'active' });

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Active session not found'
      });
    }

    // Add both messages
    await session.addMessage('user', userMessage.trim());
    await session.addMessage('bot', botMessage.trim(), metadata || {});

    console.log(`💬 Chat interaction added to session ${sessionId.substring(0, 8)}...`);

    res.status(200).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        messageCount: session.messageCount,
        lastActivity: session.lastActivity,
        messages: session.messages
      }
    });

  } catch (error) {
    console.error('❌ Error adding chat interaction:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to add chat interaction',
      message: error.message
    });
  }
};

/**
 * Get session details with all messages
 * @route GET /api/sessions/:sessionId
 */
const getSession = async (req, res) => {
  try {
    const { sessionId } = req.params;

    const session = await Session.findOne({ sessionId });

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Session not found'
      });
    }

    res.status(200).json({
      success: true,
      data: session
    });

  } catch (error) {
    console.error('❌ Error getting session:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get session',
      message: error.message
    });
  }
};

/**
 * Get messages for a session
 * @route GET /api/sessions/:sessionId/messages
 */
const getMessages = async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { limit = 100, skip = 0 } = req.query;

    const session = await Session.findOne({ sessionId });

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Session not found'
      });
    }

    // Get paginated messages
    const messages = session.messages
      .slice(parseInt(skip), parseInt(skip) + parseInt(limit));

    res.status(200).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        total: session.messages.length,
        returned: messages.length,
        messages
      }
    });

  } catch (error) {
    console.error('❌ Error getting messages:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get messages',
      message: error.message
    });
  }
};

/**
 * End a session
 * @route PUT /api/sessions/:sessionId/end
 */
const endSession = async (req, res) => {
  try {
    const { sessionId } = req.params;

    const session = await Session.findOne({ sessionId, status: 'active' });

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Active session not found'
      });
    }

    await session.endSession();

    console.log(`🔚 Session ended: ${sessionId.substring(0, 8)}...`);

    res.status(200).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        status: session.status,
        endedAt: session.endedAt,
        duration: session.duration,
        messageCount: session.messageCount
      }
    });

  } catch (error) {
    console.error('❌ Error ending session:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to end session',
      message: error.message
    });
  }
};

/**
 * Get all active sessions
 * @route GET /api/sessions/active
 */
const getActiveSessions = async (req, res) => {
  try {
    const sessions = await Session.find({ status: 'active' })
      .sort({ lastActivity: -1 })
      .select('-messages'); // Exclude messages for performance

    res.status(200).json({
      success: true,
      count: sessions.length,
      data: sessions
    });

  } catch (error) {
    console.error('❌ Error getting active sessions:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get active sessions',
      message: error.message
    });
  }
};

/**
 * Get session statistics
 * @route GET /api/sessions/stats
 */
const getSessionStats = async (req, res) => {
  try {
    const stats = await Session.getStatistics();

    res.status(200).json({
      success: true,
      data: stats
    });

  } catch (error) {
    console.error('❌ Error getting session stats:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get session statistics',
      message: error.message
    });
  }
};

/**
 * Update session activity (keep-alive)
 * @route PUT /api/sessions/:sessionId/activity
 */
const updateActivity = async (req, res) => {
  try {
    const { sessionId } = req.params;

    const session = await Session.findOneAndUpdate(
      { sessionId, status: 'active' },
      { lastActivity: new Date() },
      { new: true }
    );

    if (!session) {
      return res.status(404).json({
        success: false,
        error: 'Active session not found'
      });
    }

    res.status(200).json({
      success: true,
      data: {
        sessionId: session.sessionId,
        lastActivity: session.lastActivity
      }
    });

  } catch (error) {
    console.error('❌ Error updating activity:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update activity',
      message: error.message
    });
  }
};

/**
 * Send email summary for a session
 * @route POST /api/sessions/:sessionId/email-summary
 */
const sendSessionSummary = async (req, res) => {
  try {
    const { sessionId } = req.params;
    
    console.log(`📧 Request to send email summary for session: ${sessionId}`);
    
    // Import email service
    const { sendSummaryEmail } = require('../services/emailService');
    
    // Send the email
    const result = await sendSummaryEmail(sessionId);
    
    if (result.success) {
      res.status(200).json({
        success: true,
        message: result.message,
        data: result.details
      });
    } else {
      res.status(500).json({
        success: false,
        message: result.message,
        error: result.error
      });
    }
    
  } catch (error) {
    console.error('❌ Error sending session summary:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to send session summary',
      message: error.message
    });
  }
};

module.exports = {
  createSession,
  addUserMessage,
  addBotMessage,
  addChatInteraction,
  getSession,
  getMessages,
  endSession,
  getActiveSessions,
  getSessionStats,
  updateActivity,
  sendSessionSummary
};
