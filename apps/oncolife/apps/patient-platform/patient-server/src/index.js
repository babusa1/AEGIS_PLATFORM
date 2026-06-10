const express = require('express');
const app = express();

// Middleware to store Authorization header in res.locals for all routes
app.use((req, res, next) => {
  if (req.headers.authorization) {
    res.locals.authorization = req.headers.authorization;
  }
  next();
}); 