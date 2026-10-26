# Build from the repository root: docker build -t optiroute-frontend:local ./frontend

# Stage 1: Node builds the React application into static files.
FROM node:22-alpine AS build

WORKDIR /app

# Cache the dependency installation until the package files change.
COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js ./
COPY public/ ./public/
COPY src/ ./src/
RUN npm run build

# Stage 2: Only Nginx and the built files are needed to serve the application.
FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
