require('dotenv').config();
const mongoose = require('mongoose');
const Session = require('../models/Session');
const { buildPlainTextSummary, buildHtmlSummary } = require('../services/emailService');

(async function main() {
  const mongoUri = (process.env.MONGODB_URI || 'mongodb://localhost:27017/') + (process.env.MONGODB_DB || 'yazaki_chatbot');
  console.log('Connecting to MongoDB:', mongoUri);
  await mongoose.connect(mongoUri, { useNewUrlParser: true, useUnifiedTopology: true });

  try {
    // Create a temporary session (not relying on other scripts)
    const testSession = new Session({
      sessionId: `verify-${Date.now()}`,
      userInfo: {
        fullName: 'Verify User',
        email: 'verify.user@example.com',
        companyName: 'VerifyCo',
        supplierType: 'Current Supplier',
        location: {
          city: 'São Paulo',
          country: 'Brazil'
        }
      },
      messages: [
        { sender: 'user', text: 'Please verify location appears in email', timestamp: new Date() }
      ],
      status: 'ended',
      createdAt: new Date(Date.now() - 1000 * 60 * 20),
      updatedAt: new Date()
    });

    await testSession.save();
    console.log('Created test session:', testSession.sessionId);

    // Build summaries using the service functions
    const plain = buildPlainTextSummary(testSession.toObject());
    const html = buildHtmlSummary(testSession.toObject());

    console.log('\n--- PLAIN TEXT SUMMARY ---\n');
    console.log(plain);

    console.log('\n--- HTML SUMMARY SNIPPET (first 1200 chars) ---\n');
    console.log(html.slice(0, 1200));

    console.log('\nIf you see the Location line (city, country) in the plain text and a Location row in the HTML snippet above, the email body will include the location.');

    // cleanup: remove the test session
    await Session.deleteOne({ sessionId: testSession.sessionId });
    console.log('Cleaned up test session');

  } catch (err) {
    console.error('Error during verification:', err);
  } finally {
    await mongoose.disconnect();
    process.exit(0);
  }
})();
