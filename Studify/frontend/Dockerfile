FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

ARG VITE_API_URL=http://localhost:5000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build