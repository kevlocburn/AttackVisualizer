# Use Node.js image to build the frontend
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker caching
COPY package*.json ./

# Install dependencies using npm ci for clean and reproducible builds
RUN npm ci

# Copy the rest of the app source code
COPY . .

# Build the React app
RUN npm run build

# Use a smaller Nginx image to serve the built app
FROM nginx:alpine

# Copy the built React app to the Nginx HTML directory
COPY --from=build /app/build /usr/share/nginx/html

# Copy a custom Nginx configuration file (optional, if needed)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for Nginx
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
