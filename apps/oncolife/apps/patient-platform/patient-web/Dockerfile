# OncoLife Patient Web - Production Dockerfile
# =============================================
# Multi-stage build: Node.js build → nginx serve
# 
# NOTE: Build context should be the monorepo root to include shared packages
# docker build -f apps/patient-platform/patient-web/Dockerfile -t patient-web .

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy shared packages first (maintains directory structure for file: references)
COPY packages/ ./packages/

# Install dependencies for shared packages
WORKDIR /app/packages/ui-components
RUN npm install --legacy-peer-deps

WORKDIR /app/packages/shared-utils
RUN npm install --legacy-peer-deps

# Copy the app's package files
WORKDIR /app
COPY apps/patient-platform/patient-web/package*.json ./apps/patient-platform/patient-web/

# Set working directory to the app
WORKDIR /app/apps/patient-platform/patient-web

# Install dependencies (this will resolve file:../../../packages/* correctly)
RUN npm install --legacy-peer-deps

# Copy the rest of the app source code
COPY apps/patient-platform/patient-web/ ./

# Build arguments for API URLs (can be overridden at build time)
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_BASE_URL=ws://localhost:8000

# Set environment variables for build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL

# Build the application (use build:nocheck to skip tsc in Docker)
RUN npm run build:nocheck


# Stage 2: Production with nginx
FROM nginx:alpine AS production

# Copy custom nginx config
COPY apps/patient-platform/patient-web/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder stage
COPY --from=builder /app/apps/patient-platform/patient-web/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
