# OllyUW Agent Sandbox Template
# Desktop: Xvnc (TigerVNC) + Openbox + E2B's modified noVNC on port 6080
# Xvnc IS the X server (no Xvfb+x11vnc copy step) and we use E2B's noVNC fork
# (the one Manus uses) for smoother UX than stock apt novnc.

FROM python:3.12-slim

# Install Python agent dependencies
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

# System tools + desktop stack.
# tigervnc-standalone-server provides Xvnc which renders directly to VNC frames
# (no Xvfb framebuffer copy). Openbox is minimal (no compositor).
# thunar: file manager. xterm: terminal. xsetroot: sets background color.
# We DON'T install apt's novnc; we clone E2B's modified fork below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git jq tesseract-ocr poppler-utils \
    tigervnc-standalone-server \
    openbox \
    thunar \
    xterm \
    x11-xserver-utils \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*

# Install E2B's modified noVNC (same client Manus uses) + a fresh websockify.
# The novnc_proxy script handles the WebSocket bridge and serves the web client.
RUN git clone --depth 1 https://github.com/e2b-dev/noVNC.git /opt/noVNC \
    && git clone --depth 1 https://github.com/novnc/websockify.git /opt/noVNC/utils/websockify \
    && ln -sf /opt/noVNC/vnc.html /opt/noVNC/index.html

# Desktop startup script.
# Sequence: Xvnc -> Openbox -> gray background -> file manager + terminal -> novnc_proxy
RUN printf '%s\n' \
    '#!/bin/bash' \
    'export DISPLAY=:1' \
    '' \
    'pkill -f "Xvnc.*:1" 2>/dev/null || true' \
    'pkill -f websockify 2>/dev/null || true' \
    'pkill -f novnc_proxy 2>/dev/null || true' \
    '' \
    'Xvnc :1 -geometry 1920x1080 -depth 24 -rfbport 5900 -SecurityTypes None -localhost no -AlwaysShared &' \
    'sleep 2' \
    '' \
    'DISPLAY=:1 openbox-session &' \
    'sleep 1' \
    '' \
    'xsetroot -display :1 -solid "#1e1e2e"' \
    'DISPLAY=:1 thunar /home/user/workspace &' \
    'DISPLAY=:1 xterm -geometry 100x30+50+500 -bg "#1e1e2e" -fg "#cdd6f4" -fa "Monospace" -fs 11 &' \
    'sleep 1' \
    '' \
    'exec /opt/noVNC/utils/novnc_proxy --vnc localhost:5900 --listen 6080 --web /opt/noVNC' \
    > /usr/local/bin/start-desktop.sh

RUN chmod +x /usr/local/bin/start-desktop.sh

RUN mkdir -p /home/user/workspace && chmod 755 /home/user/workspace

# Copy agent package into the image so worker.py is available at runtime
COPY agent/ /home/user/agent/

WORKDIR /home/user/workspace
