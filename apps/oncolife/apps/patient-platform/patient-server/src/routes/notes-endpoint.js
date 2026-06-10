const express = require('express');
const router = express.Router();
const { getWithAuth, postWithAuth, updateWithAuth } = require('../utils/api.helpers');
const { apiClient } = require('../config/axios.config');

router.get('/notes/:year/:month', async (req, res) => {
    try {
        const { year, month } = req.params;
        const base = apiClient.defaults.baseURL;
        console.log(`[NOTES] GET ${base}/diary/${year}/${month}`);
        const response = await getWithAuth(`/diary/${year}/${month}`, req, res);
        return res.status(200).json(response);
    } catch (error) {
        console.error('[NOTES] List failed:', error.message);
        return res.status(500).json({ error: 'Failed to fetch notes' });
    }
});

router.post('/notes', async (req, res) => {
    try {
        const base = apiClient.defaults.baseURL;
        console.log(`[NOTES] POST ${base}/diary`);
        const response = await postWithAuth(`/diary`, req.body, req, res);
        return res.status(200).json(response);
    } catch (error) {
        console.error('[NOTES] Create failed:', error.message);
        return res.status(500).json({ error: 'Failed to create note' });
    }
});

router.patch('/notes/:noteId', async (req, res) => {
    try {
        const base = apiClient.defaults.baseURL;
        console.log(`[NOTES] PATCH ${base}/diary/${req.params.noteId}`);
        const response = await updateWithAuth(`/diary/${req.params.noteId}`, req.body, req, res);
        return res.status(200).json(response);
    } catch (error) {
        console.error('[NOTES] Update failed:', error.message);
        return res.status(500).json({ error: 'Failed to update note' });
    }
});

router.patch('/notes/:noteId/delete', async (req, res) => {
    try {
        const base = apiClient.defaults.baseURL;
        console.log(`[NOTES] PATCH ${base}/diary/${req.params.noteId}/delete`);
        const response = await updateWithAuth(`/diary/${req.params.noteId}/delete`, {}, req, res);
        return res.status(200).json(response);
    } catch (error) {
        console.error('[NOTES] Delete failed:', error.message);
        return res.status(500).json({ error: 'Failed to delete note' });
    }
});

module.exports = router;
