const express = require('express');
const router = express.Router();
const { api } = require('../utils/api.helpers');
const { apiClient } = require('../config/axios.config');

router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      console.warn('[LOGIN] Missing credentials');
      return res.status(400).json({
        success: false,
        message: 'Email and password are required',
        error: 'MISSING_CREDENTIALS'
      });
    }

    const backendBase = apiClient?.defaults?.baseURL || '<unknown>';
    console.log(`[LOGIN] Incoming login for ${email} -> POST ${backendBase}/auth/login`);

    const response = await api.post('/auth/login', {
      email,
      password
    });

    console.log(`[LOGIN] Upstream response for ${email}: success=${response.success} status=${response.status}`);

    if (!response.success) {
      console.error('[LOGIN] Upstream error details:', response.error?.details || response.error?.message);
      return res.status(response.status).json({
        success: false,
        message: response.error.message,
        error: response.error.code === 401 ? 'INVALID_CREDENTIALS' : 'AUTHENTICATION_FAILED'
      });
    }

    const { valid, message, user_status, session, tokens } = response.data;

    if (valid) {
      if (user_status === 'CONFIRMED') {
        console.log(`[LOGIN] Successful login for ${email}`);
        return res.status(200).json({
          success: true,
          message: 'Login successful',
          data: { user_status, message, tokens }
        });
      } else if (user_status === 'FORCE_CHANGE_PASSWORD') {
        console.log(`[LOGIN] Password change required for ${email}`);
        return res.status(200).json({
          success: true,
          message: 'Password change required',
          data: { user_status, message, session, requiresPasswordChange: true }
        });
      } else if (user_status === 'CHALLENGE_REQUIRED') {
        console.log(`[LOGIN] Challenge required for ${email}`);
        return res.status(200).json({
          success: true,
          message: 'Additional authentication required',
          data: { user_status, message, session, requiresChallenge: true }
        });
      }
    } else {
      console.warn(`[LOGIN] Invalid credentials for ${email}`);
      return res.status(401).json({
        success: false,
        message: message || 'Invalid email or password',
        error: 'INVALID_CREDENTIALS'
      });
    }

  } catch (error) {
    const backendBase = apiClient?.defaults?.baseURL || '<unknown>';
    console.error(`[LOGIN] Endpoint error (backend=${backendBase}):`, error?.response?.data || error.message);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
      error: 'INTERNAL_ERROR'
    });
  }
});

router.post('/complete-new-password', async (req, res) => {
  try {
    const { email, new_password, session } = req.body;

    if (!email || !new_password || !session) {
      console.warn('[LOGIN] Missing fields for complete-new-password');
      return res.status(400).json({
        success: false,
        message: 'Email, new password, and session are required',
        error: 'MISSING_FIELDS'
      });
    }

    const backendBase = apiClient?.defaults?.baseURL || '<unknown>';
    console.log(`[LOGIN] complete-new-password for ${email} -> POST ${backendBase}/auth/complete-new-password`);

    const response = await api.post('/auth/complete-new-password', {
      email,
      new_password,
      session
    });

    if (!response.success) {
      console.error('[LOGIN] Upstream error details (complete-new-password):', response.error?.details || response.error?.message);
      return res.status(response.status).json({
        success: false,
        message: response.error.message,
        error: response.error.code === 400 ? 'INVALID_REQUEST' : 'PASSWORD_CHANGE_FAILED'
      });
    }

    const { message, tokens } = response.data;

    console.log(`[LOGIN] complete-new-password success for ${email}`);
    return res.status(200).json({ success: true, message: 'Password changed successfully', data: { message, tokens } });
  } catch (error) {
    console.error('[LOGIN] complete-new-password endpoint error:', error?.response?.data || error.message);
    return res.status(500).json({ success: false, message: 'Internal server error', error: 'INTERNAL_ERROR' });
  }
});

router.post('/signup', async (req, res) => {
  try {
    const { emailAddress:email, firstName:first_name, lastName:last_name } = req.body;

    if (!email || !first_name || !last_name) {
      console.warn('[LOGIN] Missing fields for signup');
      return res.status(400).json({
        success: false,
        message: 'Email, first name, and last name are required',
        error: 'MISSING_FIELDS'
      });
    }

    const backendBase = apiClient?.defaults?.baseURL || '<unknown>';
    console.log(`[LOGIN] signup for ${email} -> POST ${backendBase}/auth/signup`);

    const response = await api.post('/auth/signup', { email, first_name, last_name });

    if (!response.success) {
      console.error('[LOGIN] Upstream error details (signup):', response.error?.details || response.error?.message);
      return res.status(response.status).json({
        success: false,
        message: response.error.message,
        error: response.error.code === 400 ? 'BAD_REQUEST' : 'SIGNUP_FAILED'
      });
    }

    const { message, email: userEmail, user_status } = response.data;

    console.log(`[LOGIN] signup success for ${email}`);
    return res.status(201).json({ success: true, message: 'User created successfully', data: { message, email: userEmail, user_status } });
  } catch (error) {
    console.error('Signup endpoint error:', error?.response?.data || error.message);
    return res.status(500).json({ success: false, message: 'Internal server error', error: 'INTERNAL_ERROR' });
  }
});

module.exports = router;
