# --- Build stage ---
FROM node:20-alpine AS build
WORKDIR /app

# Cachear deps
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copiar fuente y compilar
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_USE_MOCKS=false
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# --- Runtime stage ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
