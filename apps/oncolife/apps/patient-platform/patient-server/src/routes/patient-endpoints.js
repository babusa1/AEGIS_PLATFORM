const express = require('express');
const router = express.Router();
const { updateWithAuth } = require('../utils/api.helpers');
const { apiClient } = require('../config/axios.config');

// Update patient consent and acknowledgement flags
router.patch('/patient/update-consent', async (req, res) => {
  try {
    const base = apiClient.defaults.baseURL;
    console.log(`[PATIENT] PATCH ${base}/patient/update-consent`);
    const response = await updateWithAuth('/patient/update-consent', req.body, req, res);
    if (!response.success) {
      console.error('[PATIENT] Upstream error (update-consent):', response.error?.details || response.error?.message);
      return res.status(response.status).json({ success: false, message: response.error.message, error: 'BACKEND_ERROR', details: response.error.details });
    }
    console.log('[PATIENT] Updated consent successfully');
    return res.status(200).json(response.data);
  } catch (error) {
    console.error('[PATIENT] Forwarding update-consent failed:', error);
    return res.status(500).json({ success: false, message: 'Internal server error' });
  }
});

module.exports = router; 