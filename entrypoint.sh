#!/bin/bash

# Start the game server in the background
echo "Starting game server on port 5555..."
uv run server/server.py &

# Serve the web client on port 8080
echo "Starting web client server on port 8080..."
# pygbag build usually puts files in client/build/web
cd client/build/web
uv run -m http.server 8080
