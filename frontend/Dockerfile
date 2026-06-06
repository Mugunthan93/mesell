# frontend/Dockerfile — multi-stage per §20.C
# Stage 1: Node 20 builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy lock files first for layer caching
COPY package*.json ./
RUN npm ci --no-audit --prefer-offline

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: nginx:1.27-alpine runtime
FROM nginx:1.27-alpine AS runtime

# SPA + cache config per §20.D
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Angular build output is dist/frontend/browser (per angular.json outputPath + §20.B)
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -q -O- http://localhost/ || exit 1
