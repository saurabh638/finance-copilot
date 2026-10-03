FROM node:22-slim

WORKDIR /app

# Install dependencies first so this layer caches when only source changes.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
