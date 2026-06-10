const express = require('express');
const router = express.Router();

const healthRoutes = require('./health-endpoint');
const loginRoutes = require('./login-endpoints');
const summariesRoutes = require('./summaries-endpoint');
const notesRoutes = require('./notes-endpoint');
const profileRoutes = require('./profile-endpoint');
const chatRoutes = require('./chat-routes');
const patientRoutes = require('./patient-endpoints');

router.get('/', (req, res) => {
  res.json({
    message: 'Express Server API',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
});


router.use('/', healthRoutes);
router.use('/', loginRoutes);
router.use('/', summariesRoutes);
router.use('/', notesRoutes);
router.use('/', profileRoutes);
router.use('/chat', chatRoutes);
router.use('/', patientRoutes);

module.exports = router;