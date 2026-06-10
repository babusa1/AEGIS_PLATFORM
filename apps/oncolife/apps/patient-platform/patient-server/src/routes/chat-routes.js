const express = require('express');
const router = express.Router();
const { api } = require('../utils/api.helpers');
const { apiClient } = require('../config/axios.config');

router.get('/session/today', async (req, res) => {
  try {
    const base = apiClient.defaults.baseURL;
    console.log(`[CHAT] GET ${base}/chat/session/today`);
    const data = await api.get('/chat/session/today', {
      headers: {
        'Authorization': req.headers.authorization
      }
    });
    if (!data.success) {
      console.error('[CHAT] Upstream error (session/today):', data.error?.details || data.error?.message);
      return res.status(data.status).json({ error: 'Failed to fetch chat session', details: data.error });
    }
    return res.status(200).json(data.data);
  } catch (error) {
    console.error('Chat session error:', error);
    return res.status(error.response?.status || 500).json({
      error: 'Failed to fetch chat session',
      details: error.message
    });
  }
});

router.post('/message', async (req, res) => {
  try {
    const base = apiClient.defaults.baseURL;
    console.log(`[CHAT] POST ${base}/chat/message`);
    const data = await api.post('/chat/message', req.body, {
      headers: {
        'Authorization': req.headers.authorization
      }
    });
    if (!data.success) {
      console.error('[CHAT] Upstream error (message):', data.error?.details || data.error?.message);
      return res.status(data.status).json({ error: 'Failed to send message', details: data.error });
    }
    res.status(200).json(data);
  } catch (error) {
    console.error('Send message error:', error);
    res.status(error.response?.status || 500).json({
      error: 'Failed to send message',
      details: error.message
    });
  }
});

router.post('/session/new', async (req, res) => {
  try {
    const base = apiClient.defaults.baseURL;
    console.log(`[CHAT] POST ${base}/chat/session/new`);
    const response = await api.post('/chat/session/new', req.body, {
      headers: {
        'Authorization': req.headers.authorization
      }
    });
    if (!response.success) {
      console.error('[CHAT] Upstream error (session/new):', response.error?.details || response.error?.message);
      return res.status(response.status).json({ error: 'Failed to create new session', details: response.error });
    }
    res.status(200).json(response.data);
  } catch (error) {
    console.error('New session error:', error);
    res.status(error.response?.status || 500).json({
      error: 'Failed to create new session',
      details: error.message
    });
  }
});

// New route for chemo date logging
router.post('/chemo/log', async (req, res) => {
  try {
    const base = apiClient.defaults.baseURL;
    console.log(`[CHAT] POST ${base}/chemo/log`);
    const data = await api.post('/chemo/log', req.body, {
      headers: {
        'Authorization': req.headers.authorization
      }
    });
    if (!data.success) {
      console.error('[CHAT] Upstream error (chemo/log):', data.error?.details || data.error?.message);
      return res.status(data.status).json({ error: 'Failed to log chemotherapy date', details: data.error });
    }
    res.status(200).json(data);
  } catch (error) {
    console.error('Log chemo date error:', error);
    res.status(error.response?.status || 500).json({
      error: 'Failed to log chemotherapy date',
      details: error.message
    });
  }
});

module.exports = router; 