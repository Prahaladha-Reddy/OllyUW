# OllyUW Agent Sandbox Template
# Includes agent runtime dependencies + desktop GUI environment with VNC/noVNC

FROM python:3.12-slim

# Install Python dependencies
RUN pip install --no-cache-dir \
    redis>=5.0.0 \
    langchain-openai>=1.2.0 \
    langchain-core>=0.3.0 \
    openai>=2.0.0 \
    python-dotenv>=1.0.1 \
    tiktoken>=0.8.0 \
    mem0ai>=0.1.0 \
    parallel-web>=0.6.0 \
    langfuse>=4.0.0 \
    pdfplumber>=0.11.0 \
    pymupdf>=1.24.0 \
    pytesseract>=0.3.10 \
    pillow>=10.0.0 \
    pandas>=2.2.0

# Install system dependencies: agent tools + desktop environment
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git jq tesseract-ocr poppler-utils \
    xvfb x11-xserver-utils xfce4 xfce4-terminal \
    tigervnc-server novnc python3-websockify \
    && rm -rf /var/lib/apt/lists/*

# Create VNC directory
RUN mkdir -p /root/.vnc && chmod 700 /root/.vnc

# Create startup script for desktop environment + VNC + noVNC
RUN cat > /usr/local/bin/start-desktop.sh << 'SCRIPT'
#!/bin/bash
set -e

# Kill any existing VNC processes
pkill -f "Xvfb.*:1" || true
pkill -f "tigervncsession" || true

# Start virtual framebuffer on display :1
export DISPLAY=:1
Xvfb :1 -screen 0 1920x1080x24 &
XVFB_PID=$!
sleep 2

# Start XFCE on the virtual display
startxfce4 &
XFCE_PID=$!
sleep 3

# Start TigerVNC server on port 5901
vncserver :1 -geometry 1920x1080 -depth 24

# Start noVNC WebSocket bridge on port 6080
websockify --web=/usr/share/novnc 6080 localhost:5901 &

# Keep container alive
wait
SCRIPT
RUN chmod +x /usr/local/bin/start-desktop.sh

# Set up workspace directory for agent
RUN mkdir -p /home/user/workspace && chmod 755 /home/user/workspace

WORKDIR /home/user/workspace
