# -------- Base image --------
FROM node:20-alpine AS base
WORKDIR /app
# Do NOT set NODE_ENV=production here; we need dev deps during build

# -------- Dependencies (install all workspaces) --------
FROM base AS deps
# Copy root manifests
COPY package.json package-lock.json turbo.json ./
# Copy workspace manifests and sources needed to resolve deps and build web
COPY apps/patient-platform/patient-web/package.json ./apps/patient-platform/patient-web/package.json
COPY apps/patient-platform/patient-server/package.json ./apps/patient-platform/patient-server/package.json
COPY packages ./packages

# Optional build arg to force cache busting when needed
ARG FORCE_DEV_DEPS=0

# Install all workspaces deps including devDependencies for build (use install instead of ci)
RUN echo "FORCE_DEV_DEPS=$FORCE_DEV_DEPS" && npm install --include=dev

# -------- Build web --------
FROM deps AS build
# Copy the rest of the monorepo (only the patient platform apps)
COPY apps/patient-platform/patient-web ./apps/patient-platform/patient-web
COPY apps/patient-platform/patient-server ./apps/patient-platform/patient-server

# Accept frontend build-time config (defaults used if unset)
ARG VITE_API_BASE
ARG VITE_WS_BASE
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_WS_BASE=${VITE_WS_BASE}

# Build the patient web (outputs to apps/patient-platform/patient-web/dist)
RUN npm run build --workspace=@oncolife/patient-web

# After build, prune dev dependencies to slim final image but keep server runtime deps
RUN npm prune --omit=dev

# -------- Runtime --------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Configure port for Fly
ENV PORT=3000

# Copy node_modules and repo files required at runtime
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/apps/patient-platform/patient-server ./apps/patient-platform/patient-server
# Copy built web assets into expected path for production serving
COPY --from=build /app/apps/patient-platform/patient-web/dist ./apps/patient-platform/patient-web/dist
# Copy shared packages at runtime if server imports any runtime code from them
COPY --from=build /app/packages ./packages

EXPOSE 3000
# Start the express gateway in production mode
CMD ["npm", "start", "--workspace=@oncolife/patient-server"] 