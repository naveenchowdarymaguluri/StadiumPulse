# Stage 1: Build the React frontend using Vite
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY tsconfig.json vite.config.ts index.html tailwind.config.js postcss.config.js ./
COPY src ./src
RUN npm run build

# Stage 2: Create python server container
FROM python:3.11-slim
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI backend code
COPY backend ./backend

# Copy built React assets into root folder for FastAPI static mount
COPY --from=frontend-builder /app/dist ./dist

EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
