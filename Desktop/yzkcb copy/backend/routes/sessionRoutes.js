/**
 * Session Routes
 * 
 * Defines all API endpoints for session management
 */

const express = require('express');
const router = express.Router();
const { body, param, query, validationResult } = require('express-validator');
const {
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
} = require('../controllers/sessionController');

/**
 * Validation middleware
 */
const validate = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      success: false,
      errors: errors.array()
    });
  }
  next();
};

/**
 * @route   POST /api/sessions
 * @desc    Create a new chat session
 * @access  Public
 */
router.post(
  '/',
  [
    body('userInfo').isObject().withMessage('userInfo must be an object'),
    body('userInfo.fullName').trim().notEmpty().withMessage('Full name is required'),
    body('userInfo.email').isEmail().withMessage('Valid email is required'),
    body('userInfo.companyName').trim().notEmpty().withMessage('Company name is required'),
    body('userInfo.supplierType')
      .isIn(['New Supplier', 'Current Supplier'])
      .withMessage('Supplier type must be New Supplier or Current Supplier'),
    validate
  ],
  createSession
);

/**
 * @route   POST /api/sessions/:sessionId/messages/user
 * @desc    Add a user message to session
 * @access  Public
 */
router.post(
  '/:sessionId/messages/user',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    body('text').trim().notEmpty().withMessage('Message text is required'),
    validate
  ],
  addUserMessage
);

/**
 * @route   POST /api/sessions/:sessionId/messages/bot
 * @desc    Add a bot message to session
 * @access  Public
 */
router.post(
  '/:sessionId/messages/bot',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    body('text').trim().notEmpty().withMessage('Message text is required'),
    body('metadata').optional().isObject(),
    validate
  ],
  addBotMessage
);

/**
 * @route   POST /api/sessions/:sessionId/chat
 * @desc    Add complete chat interaction (user + bot messages)
 * @access  Public
 */
router.post(
  '/:sessionId/chat',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    body('userMessage').trim().notEmpty().withMessage('User message is required'),
    body('botMessage').trim().notEmpty().withMessage('Bot message is required'),
    body('metadata').optional().isObject(),
    validate
  ],
  addChatInteraction
);

/**
 * @route   GET /api/sessions/:sessionId
 * @desc    Get session details with all messages
 * @access  Public
 */
router.get(
  '/:sessionId',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    validate
  ],
  getSession
);

/**
 * @route   GET /api/sessions/:sessionId/messages
 * @desc    Get messages for a session (paginated)
 * @access  Public
 */
router.get(
  '/:sessionId/messages',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    query('limit').optional().isInt({ min: 1, max: 1000 }),
    query('skip').optional().isInt({ min: 0 }),
    validate
  ],
  getMessages
);

/**
 * @route   PUT /api/sessions/:sessionId/end
 * @desc    End a session
 * @access  Public
 */
router.put(
  '/:sessionId/end',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    validate
  ],
  endSession
);

/**
 * @route   PUT /api/sessions/:sessionId/activity
 * @desc    Update session activity (keep-alive)
 * @access  Public
 */
router.put(
  '/:sessionId/activity',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    validate
  ],
  updateActivity
);

/**
 * @route   POST /api/sessions/:sessionId/email-summary
 * @desc    Send email summary for a session to admin
 * @access  Public
 */
router.post(
  '/:sessionId/email-summary',
  [
    param('sessionId').isUUID().withMessage('Invalid session ID'),
    validate
  ],
  sendSessionSummary
);

/**
 * @route   GET /api/sessions/active/list
 * @desc    Get all active sessions
 * @access  Public
 */
router.get('/active/list', getActiveSessions);

/**
 * @route   GET /api/sessions/stats/summary
 * @desc    Get session statistics
 * @access  Public
 */
router.get('/stats/summary', getSessionStats);

module.exports = router;
