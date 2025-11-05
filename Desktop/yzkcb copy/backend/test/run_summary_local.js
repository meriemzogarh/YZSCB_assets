const { buildPlainTextSummary, buildHtmlSummary } = require('../services/emailService');

const session = {
  sessionId: 'test-session-1',
  userInfo: {
    fullName: 'Alice Example',
    email: 'alice@example.com',
    companyName: 'ACME Ltd',
    supplierType: 'Preferred',
    city: 'Tokyo',
    country: 'Japan'
  },
  messages: [
    { sender: 'user', text: 'Hello', timestamp: new Date() }
  ],
  status: 'ended',
  createdAt: new Date(Date.now() - 1000 * 60 * 30),
  updatedAt: new Date()
};

console.log('--- Plain Text Summary ---\n');
console.log(buildPlainTextSummary(session));

console.log('\n--- HTML Summary (snippet) ---\n');
const html = buildHtmlSummary(session);
console.log(html.slice(0, 1000));
console.log('\n(HTML output truncated)');
