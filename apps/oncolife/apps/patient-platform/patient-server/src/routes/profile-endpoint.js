const express = require('express');
const router = express.Router();
const { getWithAuth } = require('../utils/api.helpers');
const { apiClient } = require('../config/axios.config');

router.get('/profile', async (req, res) => {
  try {
    const base = apiClient.defaults.baseURL;
    console.log(`[PROFILE] GET ${base}/profile`);
    const response = await getWithAuth('/profile', req, res);
    if (response.success) {
      console.log('[PROFILE] Profile fetched OK');
      return res.status(200).json(response.data);
    } else {
      console.error('[PROFILE] Upstream error:', response.error?.details || response.error?.message);
      return res.status(response.status).json({ error: response.error });
    }
  } catch (error) {
    console.error('[PROFILE] Route error:', error.message);
    return res.status(500).json({ error: 'Failed to fetch profile' });
  }
});

module.exports = router;
