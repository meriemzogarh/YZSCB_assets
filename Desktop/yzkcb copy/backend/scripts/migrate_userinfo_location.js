// Migration: Move flat userInfo.city/country into userInfo.location
// Usage: node backend/scripts/migrate_userinfo_location.js
// Make sure MONGODB_URI and MONGODB_DB are set in your environment or .env

require('dotenv').config();
const mongoose = require('mongoose');
const Session = require('../models/Session');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/';
const MONGODB_DB = process.env.MONGODB_DB || 'yazaki_chatbot';

const run = async () => {
  const uri = MONGODB_URI;
  console.log('Connecting to MongoDB:', uri + MONGODB_DB);
  await mongoose.connect(uri + MONGODB_DB, {
    useNewUrlParser: true,
    useUnifiedTopology: true
  });

  try {
    // Find sessions that have flat fields or missing location
    const cursor = Session.find({
      $or: [
        { 'userInfo.city': { $exists: true } },
        { 'userInfo.country': { $exists: true } },
        { 'userInfo.location': { $exists: false } }
      ]
    }).cursor();

    let updated = 0;
    for (let doc = await cursor.next(); doc != null; doc = await cursor.next()) {
      const ui = doc.userInfo || {};
      const city = ui.city || (ui.location && ui.location.city);
      const country = ui.country || (ui.location && ui.location.country);

      // Only update if we have any location info
      if (city || country) {
        doc.userInfo = doc.userInfo || {};
        doc.userInfo.location = doc.userInfo.location || {};
        if (city) doc.userInfo.location.city = city;
        if (country) doc.userInfo.location.country = country;

        // Remove flat fields if present
        if (doc.userInfo.city) delete doc.userInfo.city;
        if (doc.userInfo.country) delete doc.userInfo.country;

        await doc.save();
        updated += 1;
        console.log(`Updated session ${doc.sessionId}: location set to ${city || ''}${city && country ? ', ' : ''}${country || ''}`);
      } else if (!doc.userInfo.location) {
        // Ensure there is a location object (even empty) to avoid future issues
        doc.userInfo = doc.userInfo || {};
        doc.userInfo.location = doc.userInfo.location || {};
        await doc.save();
        updated += 1;
        console.log(`Normalized session ${doc.sessionId}: added empty location object`);
      }
    }

    console.log(`Migration completed. Documents updated: ${updated}`);
  } catch (err) {
    console.error('Migration error:', err);
  } finally {
    await mongoose.disconnect();
    process.exit(0);
  }
};

run();
