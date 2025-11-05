/**
 * Test Script for Email Service
 * 
 * This script helps test the sendSummaryEmail function
 * Usage: node backend/test/testEmailService.js [sessionId]
 */

require('dotenv').config();
const { connectDB } = require('../config/database');
const { sendSummaryEmail } = require('../services/emailService');
const Session = require('../models/Session');

/**
 * Create a test session in MongoDB
 */
const createTestSession = async () => {
  const testSession = new Session({
    sessionId: '550e8400-e29b-41d4-a716-446655440000',
    userInfo: {
      fullName: 'John Doe',
      email: 'john.doe@example.com',
      companyName: 'Example Corp',
      supplierType: 'New Supplier',
      // store location in the nested `location` object to match the Mongoose schema
      location: {
        city: 'Berlin',
        country: 'Germany'
      }
    },
    messages: [
      {
        sender: 'user',
        text: 'Hello, I have a question about supplier claims.',
        timestamp: new Date('2025-10-20T10:15:00Z')
      },
      {
        sender: 'bot',
        text: 'Sure! Please describe the issue you\'re experiencing with supplier claims.',
        timestamp: new Date('2025-10-20T10:15:30Z')
      },
      {
        sender: 'user',
        text: 'What documentation is required for a quality claim?',
        timestamp: new Date('2025-10-20T10:16:00Z')
      },
      {
        sender: 'bot',
        text: `For quality claims, you need to provide the following documentation:
1. Detailed problem description
2. Part numbers and quantities affected
3. Photos or samples of defective parts
4. PPAP documentation if available
5. 8D report (if applicable)`,
        timestamp: new Date('2025-10-20T10:16:45Z'),
        metadata: {
          confidence: 0.95,
          sources: ['SQCM', 'Supplier_Quality_Manual']
        }
      },
      {
        sender: 'user',
        text: 'How long does it take to process a claim?',
        timestamp: new Date('2025-10-20T10:17:30Z')
      },
      {
        sender: 'bot',
        text: 'Typical processing time is 5-10 business days from receipt of complete documentation.',
        timestamp: new Date('2025-10-20T10:17:45Z'),
        metadata: {
          confidence: 0.88
        }
      }
    ],
    status: 'ended',
    createdAt: new Date('2025-10-20T10:15:00Z'),
    lastActivity: new Date('2025-10-20T10:48:00Z')
  });

  await testSession.save();
  console.log('✅ Test session created:', testSession.sessionId);
  return testSession.sessionId;
};

/**
 * Test the email service
 */
const testEmailService = async (sessionId) => {
  try {
    console.log('\n🧪 Testing Email Service\n');
    console.log('═══════════════════════════════════════\n');
    
    // Check configuration
    console.log('📋 Configuration Check:');
    console.log(`   MAIL_HOST: ${process.env.MAIL_HOST || '❌ Not set'}`);
    console.log(`   MAIL_PORT: ${process.env.MAIL_PORT || '❌ Not set'}`);
    console.log(`   MAIL_USER: ${process.env.MAIL_USER ? '✅ Set' : '❌ Not set'}`);
    console.log(`   MAIL_PASS: ${process.env.MAIL_PASS ? '✅ Set' : '❌ Not set'}`);
    console.log(`   ADMIN_EMAIL: ${process.env.ADMIN_EMAIL || '❌ Not set'}\n`);
    
    if (!process.env.MAIL_USER || !process.env.MAIL_PASS || !process.env.ADMIN_EMAIL) {
      throw new Error('Missing required email configuration. Please check your .env file.');
    }
    
    console.log('───────────────────────────────────────\n');
    
    // Connect to MongoDB
    console.log('📦 Connecting to MongoDB...');
    await connectDB();
    console.log('✅ MongoDB connected\n');
    
    console.log('───────────────────────────────────────\n');
    
    // Create test session if no sessionId provided
    let testSessionId = sessionId;
    if (!testSessionId) {
      console.log('💡 No session ID provided, creating test session...');
      testSessionId = await createTestSession();
      console.log('\n');
    }
    
    console.log('───────────────────────────────────────\n');
    
    // Send email
    console.log(`📧 Sending summary email for session: ${testSessionId}\n`);
    const result = await sendSummaryEmail(testSessionId);
    
    console.log('\n───────────────────────────────────────\n');
    
    // Display result
    if (result.success) {
      console.log('✅ TEST PASSED!\n');
      console.log('📨 Email Details:');
      console.log(`   Message: ${result.message}`);
      console.log(`   Message ID: ${result.messageId}`);
      console.log(`   Sent to: ${result.details.recipient}`);
      console.log(`   User: ${result.details.userName}`);
      if (result.details.userLocation) console.log(`   Location: ${result.details.userLocation}`);
      console.log(`   Messages: ${result.details.messageCount}`);
      console.log(`   Timestamp: ${result.timestamp}\n`);
    } else {
      console.log('❌ TEST FAILED!\n');
      console.log(`   Error: ${result.message}`);
      console.log(`   Details: ${result.error}\n`);
    }
    
    console.log('═══════════════════════════════════════\n');
    
  } catch (error) {
    console.error('\n❌ TEST ERROR:\n');
    console.error(`   ${error.message}\n`);
    console.error('Stack trace:');
    console.error(error.stack);
  } finally {
    // Close MongoDB connection
    process.exit(0);
  }
};

// Main execution
const main = async () => {
  // Get session ID from command line argument
  const sessionId = process.argv[2];
  
  console.log('\n');
  console.log('╔═══════════════════════════════════════╗');
  console.log('║   Email Service Test Suite            ║');
  console.log('║   Yazaki Chatbot Backend              ║');
  console.log('╚═══════════════════════════════════════╝');
  
  await testEmailService(sessionId);
};

// Handle unhandled rejections
process.on('unhandledRejection', (error) => {
  console.error('\n❌ Unhandled Promise Rejection:', error);
  process.exit(1);
});

// Run the test
main();
