FROM node:22-slim AS deps
WORKDIR /app
COPY web/package.json web/package-lock.json* ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY web ./
# NEXUS_API_BASE_URL/NEXUS_API_KEY are read at request time (server-only route handlers),
# not baked in at build time, so no build-arg plumbing is needed here.
RUN npm run build

# `output: "standalone"` (next.config.ts) traces only the dependencies actually reachable
# at runtime, so the final image doesn't need the full node_modules tree or dev toolchain.
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
