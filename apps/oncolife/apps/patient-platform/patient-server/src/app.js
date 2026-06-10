require('dotenv').config();
const express = require('express');
const configureMiddleware = require('./config/config.middleware');
const { createWsProxies } = require('./config/config.middleware');
const routes = require('./routes');

const app = express();

// Configure basic middleware (CORS, body parsing, etc.)
app.use(require('cors')({
  origin: ['http://localhost:3000', 'http://localhost:5173'],
  credentials: true
}));

if (process.env.NODE_ENV !== 'test') {
  app.use(require('morgan')('combined'));
}

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Mount Express API routes FIRST (these take precedence over proxy)
app.use('/api', routes);

// Configure proxy middleware (for routes not handled by Express)
configureMiddleware(app);

// 404 handler for API routes only
app.use('/api/*', (req, res) => {
  res.status(404).json({
    error: 'API route not found',
    path: req.originalUrl,
    method: req.method
  });
});

const PORT = process.env.PORT || 3000;

// Start server
const server = app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🌐 URL: http://localhost:${PORT}`);
});

// Ensure WS upgrade requests are proxied when hitting this gateway directly
const { wsProxyNoRewrite, wsProxyWithRewrite } = createWsProxies();
server.on('upgrade', (req, socket, head) => {
  const url = req.url || '';
  if (url.startsWith('/api/chat/ws')) {
    // Manually rewrite path for upgrade requests to match FastAPI route
    req.url = url.replace(/^\/api\/chat\/ws/, '/chat/ws');
    wsProxyWithRewrite.upgrade(req, socket, head);
  } else if (url.startsWith('/chat/ws')) {
    wsProxyNoRewrite.upgrade(req, socket, head);
  }
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`${signal} received, shutting down gracefully`);
  server.close(() => {
    console.log('Process terminated');
    process.exit(0);
  });
};

process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

module.exports = server;