# Imagen del dashboard (Next.js en modo standalone). Sin dependencias de desarrollo en la imagen final.
FROM node:22-alpine AS deps
WORKDIR /srv/dashboard
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /srv/dashboard
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /srv/dashboard/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS run
WORKDIR /srv/dashboard
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /srv/dashboard/.next/standalone ./
COPY --from=build --chown=node:node /srv/dashboard/.next/static ./.next/static
COPY --from=build --chown=node:node /srv/dashboard/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
