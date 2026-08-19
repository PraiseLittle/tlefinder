# syntax=docker/dockerfile:1.7

FROM node:22.14.0-alpine3.21@sha256:9bef0ef1e268f60627da9ba7d7605e8831d5b56ad07487d24d1aa386336d1944 AS build

WORKDIR /build/gui

COPY gui/package.json gui/package-lock.json ./
RUN npm ci \
    && npm audit --audit-level=high

COPY gui/ ./
RUN npm test \
    && npm run typecheck \
    && npm run build \
    && ! grep -RF "http://api:2626" dist


FROM nginxinc/nginx-unprivileged:1.27.4-alpine3.21@sha256:62a904036bfc0e4a4f2b556e34cbf17bc136b47fde8cdb4628762725f48c5782 AS runtime

COPY --chown=nginx:nginx gui/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /build/gui/dist /usr/share/nginx/html

USER nginx
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["wget", "--quiet", "--output-document=/dev/null", "http://127.0.0.1:8080/"]

CMD ["nginx", "-g", "daemon off;"]
