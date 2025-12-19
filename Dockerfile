FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for pygame/pygbag
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy the project files
COPY . .

# Build the client for web using pygbag
# Note: This creates the client/build/web directory
RUN pygbag --build client/

# Expose the web server port and the game server port
EXPOSE 8080
EXPOSE 5555

# Ensure the entrypoint script is executable
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
