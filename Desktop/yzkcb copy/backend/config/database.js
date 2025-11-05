/**
 * Database Configuration
 * 
 * Handles MongoDB connection with Mongoose
 */

const mongoose = require('mongoose');

/**
 * Connect to MongoDB
 * @param {string} mongoUri - MongoDB connection string
 * @returns {Promise<void>}
 */
const connectDB = async (mongoUri) => {
  try {
    const options = {
      // Connection options
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
      family: 4 // Use IPv4
    };

    await mongoose.connect(mongoUri, options);

    console.log('✅ MongoDB Connected Successfully');
    console.log(`   Database: ${mongoose.connection.name}`);
    console.log(`   Host: ${mongoose.connection.host}`);

    // Connection event handlers
    mongoose.connection.on('error', (err) => {
      console.error('❌ MongoDB connection error:', err);
    });

    mongoose.connection.on('disconnected', () => {
      console.warn('⚠️  MongoDB disconnected');
    });

    mongoose.connection.on('reconnected', () => {
      console.log('✅ MongoDB reconnected');
    });

    // Graceful shutdown
    process.on('SIGINT', async () => {
      await mongoose.connection.close();
      console.log('👋 MongoDB connection closed through app termination');
      process.exit(0);
    });

  } catch (error) {
    console.error('❌ MongoDB connection failed:', error.message);
    process.exit(1);
  }
};

/**
 * Get connection status
 * @returns {object} Connection status information
 */
const getConnectionStatus = () => {
  const state = mongoose.connection.readyState;
  const states = {
    0: 'disconnected',
    1: 'connected',
    2: 'connecting',
    3: 'disconnecting'
  };

  return {
    status: states[state],
    database: mongoose.connection.name,
    host: mongoose.connection.host
  };
};

module.exports = {
  connectDB,
  getConnectionStatus
};
