const { apiClient } = require('../config/axios.config');

const api = {
  get: async (url, config = {}) => {
    try {
      const response = await apiClient.get(url, config);
      return {
        success: true,
        status: response.status,
        data: response.data,
        error: null
      };
    } catch (error) {
      return {
        success: false,
        status: error.response?.status || 500,
        data: null,
        error: {
          message: error.response?.data?.detail || error.message || 'Request failed',
          code: error.response?.status || 500,
          details: error.response?.data || error.message
        }
      };
    }
  },

  post: async (url, data = {}, config = {}) => {
    try {
      const response = await apiClient.post(url, data, config);
      return {
        success: true,
        status: response.status,
        data: response.data,
        error: null
      };
    } catch (error) {
      return {
        success: false,
        status: error.response?.status || 500,
        data: null,
        error: {
          message: error.response?.data?.detail || error.message || 'Request failed',
          code: error.response?.status || 500,
          details: error.response?.data || error.message
        }
      };
    }
  },

  put: async (url, data = {}, config = {}) => {
    try {
      const response = await apiClient.put(url, data, config);
      return {
        success: true,
        status: response.status,
        data: response.data,
        error: null
      };
    } catch (error) {
      return {
        success: false,
        status: error.response?.status || 500,
        data: null,
        error: {
          message: error.response?.data?.detail || error.message || 'Request failed',
          code: error.response?.status || 500,
          details: error.response?.data || error.message
        }
      };
    }
  },

  delete: async (url, config = {}) => {
    try {
      const response = await apiClient.delete(url, config);
      return {
        success: true,
        status: response.status,
        data: response.data,
        error: null
      };
    } catch (error) {
      return {
        success: false,
        status: error.response?.status || 500,
        data: null,
        error: {
          message: error.response?.data?.detail || error.message || 'Request failed',
          code: error.response?.status || 500,
          details: error.response?.data || error.message
        }
      };
    }
  },

  patch: async (url, data = {}, config = {}) => {
    try {
      const response = await apiClient.patch(url, data, config);
      return {
        success: true,
        status: response.status,
        data: response.data,
        error: null
      };
    } catch (error) {
      return {
        success: false,
        status: error.response?.status || 500,
        data: null,
        error: {
          message: error.response?.data?.detail || error.message || 'Request failed',
          code: error.response?.status || 500,
          details: error.response?.data || error.message
        }
      };
    }
  },
};

// Helper to always include Authorization from res.locals if present
const getWithAuth = async (url, req, res) => {
  const config = {};
  if (req.headers.authorization) {
    config.headers = { Authorization: req.headers.authorization };
  }
  return api.get(url, config);
};

const postWithAuth = async (url, data, req, res) => {
  const config = {};
  if (req.headers.authorization) {
    config.headers = { Authorization: req.headers.authorization };
  }
  return api.post(url, data, config);
};

const updateWithAuth = async (url, data, req, res) => {
  const config = {};
  if (req.headers.authorization) {
    config.headers = { Authorization: req.headers.authorization };
  }
  return api.patch(url, data, config);
};

const deleteWithAuth = async (url, req, res) => {
  const config = {};
  if (req.headers.authorization) {
    config.headers = { Authorization: req.headers.authorization };
  }
  return api.delete(url, config);
};

module.exports = {
  api,
  getWithAuth,
  postWithAuth,
  updateWithAuth,
  deleteWithAuth,
}; 