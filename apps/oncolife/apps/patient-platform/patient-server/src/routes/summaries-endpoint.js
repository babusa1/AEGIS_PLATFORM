const express = require('express');
const router = express.Router();
const { getWithAuth } = require('../utils/api.helpers');
const { apiClient } = require('../config/axios.config');

router.get('/summaries/:year/:month', async (req, res) => {
    try {
        const { year, month } = req.params;
        const base = apiClient.defaults.baseURL;
        console.log(`[SUMMARIES] GET ${base}/summaries/${year}/${month}`);
        const response = await getWithAuth(`/summaries/${year}/${month}`, req, res);
        res.status(200).json(response);
    } catch (error) {
        console.error('[SUMMARIES] Route error (list):', error.message);
        res.status(500).json({ error: 'Failed to fetch summaries' });
    }
});

router.get('/summaries/:summaryId', async (req, res) => {
    try {
        const { summaryId } = req.params;
        const base = apiClient.defaults.baseURL;
        console.log(`[SUMMARIES] GET ${base}/summaries/${summaryId}`);
        const response = await getWithAuth(`/summaries/${summaryId}`, req, res);
        res.status(200).json(response);
    } catch (error) {
        console.error('[SUMMARIES] Route error (detail):', error.message);
        res.status(500).json({ error: 'Failed to fetch summary details' });
    }
});

module.exports = router;