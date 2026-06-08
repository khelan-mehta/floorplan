# syntax=docker/dockerfile:1

# --- dev: Vite dev server with hot reload (used by docker-compose, target: dev) ---
FROM node:22-slim AS dev
ENV CI=1
WORKDIR /repo
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json apps/web/package.json
COPY packages/schemas/package.json packages/schemas/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/geometry-core/package.json packages/geometry-core/package.json
RUN pnpm install --frozen-lockfile || pnpm install
COPY . .
WORKDIR /repo/apps/web
EXPOSE 5173
CMD ["pnpm", "dev", "--host"]

# --- build: produce the static bundle ---
FROM dev AS build
RUN pnpm --filter @fpg/web build

# --- prod: serve the static bundle via nginx on :80 (default target for CI/k8s) ---
FROM nginx:1.27-alpine AS prod
COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
# SPA fallback so client-side routes resolve to index.html
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  location / { try_files $uri /index.html; }\n}\n' \
    > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
