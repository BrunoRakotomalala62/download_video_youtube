# YouTube Video Download API

## Overview
This is a Node.js API for downloading YouTube videos with quality selection support.

## Project Structure
- `server.js` - Main Express server with download endpoint
- `package.json` - Project dependencies and scripts

## Tech Stack
- Node.js 20
- Express.js - Web framework
- @distube/ytdl-core - YouTube video download library

## API Endpoints

### GET /
Returns API documentation and usage information.

### GET /download
Downloads a YouTube video.

**Parameters:**
- `video_url` (required) - YouTube video URL
- `qualite` (optional, default: 360p) - Video quality (144p, 240p, 360p, 480p, 720p, 1080p)

## Running the Project
The server runs on port 5000 with the command `node server.js`.

## Recent Changes
- 2025-11-27: Initial setup with YouTube download API
