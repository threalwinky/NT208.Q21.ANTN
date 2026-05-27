FROM node:22-alpine AS deps

WORKDIR /app
COPY package*.json ./
RUN npm ci

# ── Development stage: deps installed, source is bind-mounted ─────────────────
FROM deps AS development
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ── Builder stage: full production build ──────────────────────────────────────
FROM deps AS builder
COPY . .
RUN npm run build

# ── Production stage: minimal runtime ─────────────────────────────────────────
FROM node:22-alpine AS production
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
