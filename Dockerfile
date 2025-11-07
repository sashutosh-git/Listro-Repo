# -------- Build Stage --------
FROM node:20 AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source files
COPY . .

# Build the frontend (Vite)
RUN npm run build

# -------- Serve Stage --------
FROM nginx:alpine

# Copy build output to Nginx folder
COPY --from=build /app/dist /usr/share/nginx/html

# Change Nginx to listen on port 8080 (required by Cloud Run)
RUN sed -i 's/listen\s\+80;/listen 8080;/' /etc/nginx/conf.d/default.conf

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
