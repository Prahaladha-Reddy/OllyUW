# OllyUW Agent Sandbox Template
# Stack: Ubuntu 24.04 + XFCE4 (compositor off) + KasmVNC
#
# Why Ubuntu 24.04: python:3.12-slim lacks dbus, machine-id, and session
# bootstrap machinery. Every attempt on slim produced "Unable to contact
# settings server" or broken .desktop errors. Ubuntu has all of this.
# E2B's own desktop template uses Ubuntu for the same reason.
#
# Why KasmVNC: single binary replacing Xvfb + x11vnc + websockify + noVNC.
# Binary WebSocket framing, WebP encoding, ~2-3x smoother than noVNC.
# Built-in web client served at / on port 6901.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    HOME=/home/user \
    USER=user \
    SHELL=/bin/bash \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# Ubuntu 24.04 base already ships a 'user' account (uid 1000).
# We just ensure it has passwordless sudo so apt install works from the desktop.
RUN id user 2>/dev/null || useradd -m -s /bin/bash -u 1000 user \
 && echo "user ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/user \
 && chmod 0440 /etc/sudoers.d/user

# System base + Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git jq sudo procps \
      python3 python3-pip python3-venv python3-dev \
      build-essential \
      tesseract-ocr poppler-utils \
 && rm -rf /var/lib/apt/lists/*

# Python agent dependencies.
# --break-system-packages: Ubuntu 24.04 enforces PEP 668. Fine in a
# disposable container.
RUN pip3 install --no-cache-dir --break-system-packages \
    "redis>=5.0.0" \
    "langchain-openai>=1.2.0" \
    "langchain-core>=0.3.0" \
    "openai>=2.0.0" \
    "python-dotenv>=1.0.1" \
    "tiktoken>=0.8.0" \
    "mem0ai>=0.1.0" \
    "parallel-web>=0.6.0" \
    "langfuse>=4.0.0" \
    "pdfplumber>=0.11.0" \
    "pymupdf>=1.24.0" \
    "pytesseract>=0.3.10" \
    "pillow>=10.0.0" \
    "pandas>=2.2.0"

# XFCE desktop + real-PC apps.
# adwaita + gnome icon themes prevent missing-icon squares.
# fonts-* prevent the broken-font look on first boot.
RUN apt-get update && apt-get install -y --no-install-recommends \
      xfce4 xfce4-goodies xfce4-terminal \
      xfce4-taskmanager xfce4-screenshooter \
      dbus-x11 \
      xauth x11-utils x11-xserver-utils \
      adwaita-icon-theme gnome-icon-theme hicolor-icon-theme \
      fonts-liberation fonts-dejavu fonts-noto-core \
      thunar thunar-archive-plugin mousepad ristretto \
      file-roller galculator \
 && rm -rf /var/lib/apt/lists/*

# Generate machine-id so dbus session start works.
# Without this xfconfd fails to connect and XFCE throws "Unable to contact
# settings server" on every start.
RUN dbus-uuidgen | tee /etc/machine-id /var/lib/dbus/machine-id > /dev/null

# Remove .desktop files that reference unavailable alternatives.
# They produce error popups in Thunar/xfdesktop on first boot.
RUN rm -f /usr/share/applications/debian-uxterm.desktop \
          /usr/share/applications/debian-xterm.desktop \
          /usr/share/applications/lxde-x-www-browser.desktop \
          2>/dev/null || true

# Firefox from Mozilla's apt repo.
# On Ubuntu 22.04+ `apt install firefox` is a snap stub that does not work
# inside a container. The Mozilla repo gives the real .deb.
RUN install -d -m 0755 /etc/apt/keyrings \
 && wget -qO- https://packages.mozilla.org/apt/repo-signing-key.gpg \
    | tee /etc/apt/keyrings/packages.mozilla.org.asc > /dev/null \
 && echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" \
    > /etc/apt/sources.list.d/mozilla.list \
 && printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n' \
    > /etc/apt/preferences.d/mozilla \
 && apt-get update && apt-get install -y --no-install-recommends firefox \
 && rm -rf /var/lib/apt/lists/*

# KasmVNC: replaces Xvfb + x11vnc + websockify + noVNC in one binary.
# noble = Ubuntu 24.04 codename.
ARG KASMVNC_VERSION=1.3.4
RUN wget -qO /tmp/kasmvnc.deb \
      "https://github.com/kasmtech/KasmVNC/releases/download/v${KASMVNC_VERSION}/kasmvncserver_noble_${KASMVNC_VERSION}_amd64.deb" \
 && apt-get update \
 && apt-get install -y --no-install-recommends /tmp/kasmvnc.deb \
 && rm /tmp/kasmvnc.deb \
 && rm -rf /var/lib/apt/lists/*

# Per-user directories
RUN install -d -o user -g user \
      /home/user/.config/xfce4/xfconf/xfce-perchannel-xml \
      /home/user/.vnc \
      /home/user/.cache \
      /home/user/.local/share \
      /home/user/Desktop \
      /home/user/Documents \
      /home/user/workspace

# xfwm4: compositor OFF. This is the latency win for VNC streaming.
RUN printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<channel name="xfwm4" version="1.0">' \
    '  <property name="general" type="empty">' \
    '    <property name="use_compositing" type="bool" value="false"/>' \
    '    <property name="theme" type="string" value="Default"/>' \
    '    <property name="workspace_count" type="int" value="1"/>' \
    '  </property>' \
    '</channel>' \
    > /home/user/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml

# xfdesktop: dark solid wallpaper + desktop icons.
RUN printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<channel name="xfce4-desktop" version="1.0">' \
    '  <property name="backdrop" type="empty">' \
    '    <property name="screen0" type="empty">' \
    '      <property name="monitorscreen" type="empty">' \
    '        <property name="workspace0" type="empty">' \
    '          <property name="color-style" type="int" value="0"/>' \
    '          <property name="image-style" type="int" value="0"/>' \
    '          <property name="rgba1" type="array">' \
    '            <value type="double" value="0.117"/>' \
    '            <value type="double" value="0.117"/>' \
    '            <value type="double" value="0.180"/>' \
    '            <value type="double" value="1.000"/>' \
    '          </property>' \
    '        </property>' \
    '      </property>' \
    '    </property>' \
    '  </property>' \
    '  <property name="desktop-icons" type="empty">' \
    '    <property name="style" type="int" value="2"/>' \
    '    <property name="file-icons" type="empty">' \
    '      <property name="show-home" type="bool" value="true"/>' \
    '      <property name="show-filesystem" type="bool" value="true"/>' \
    '      <property name="show-trash" type="bool" value="true"/>' \
    '      <property name="show-removable" type="bool" value="false"/>' \
    '    </property>' \
    '  </property>' \
    '</channel>' \
    > /home/user/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml

# Icon theme + GTK defaults so icons and fonts render correctly.
RUN printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<channel name="xsettings" version="1.0">' \
    '  <property name="Net" type="empty">' \
    '    <property name="ThemeName" type="string" value="Adwaita"/>' \
    '    <property name="IconThemeName" type="string" value="Adwaita"/>' \
    '  </property>' \
    '  <property name="Gtk" type="empty">' \
    '    <property name="FontName" type="string" value="Sans 10"/>' \
    '    <property name="MonospaceFontName" type="string" value="Monospace 10"/>' \
    '    <property name="CursorThemeName" type="string" value="Adwaita"/>' \
    '  </property>' \
    '</channel>' \
    > /home/user/.config/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml

# KasmVNC config: plain HTTP (E2B proxy handles TLS), no auth, 1920x1080.
RUN printf '%s\n' \
    'network:' \
    '  protocol: http' \
    '  websocket_port: 6901' \
    '  interface: 0.0.0.0' \
    '  ssl:' \
    '    require_ssl: false' \
    'desktop:' \
    '  resolution:' \
    '    width: 1920' \
    '    height: 1080' \
    '  allow_resize: true' \
    'logging:' \
    '  log_writer_name: all' \
    '  log_dest: logfile' \
    '  level: 30' \
    'security:' \
    '  brute_force_protection:' \
    '    blacklist_threshold: 99999' \
    '    blacklist_timeout: 0' \
    > /home/user/.vnc/kasmvnc.yaml

# xstartup is run by kasmvncserver when it starts the X session.
# dbus-launch wraps startxfce4 so xfconfd and other session services connect.
RUN printf '%s\n' \
    '#!/bin/bash' \
    'unset SESSION_MANAGER' \
    'unset DBUS_SESSION_BUS_ADDRESS' \
    'export XDG_RUNTIME_DIR=/tmp/runtime-1000' \
    'export XDG_CONFIG_HOME=$HOME/.config' \
    'export XDG_DATA_HOME=$HOME/.local/share' \
    'export XDG_CACHE_HOME=$HOME/.cache' \
    'mkdir -p $XDG_RUNTIME_DIR && chmod 700 $XDG_RUNTIME_DIR' \
    'exec dbus-launch --exit-with-session startxfce4' \
    > /home/user/.vnc/xstartup \
 && chmod +x /home/user/.vnc/xstartup

# Seed a dummy password file. kasmvncserver -disableBasicAuth ignores it
# but may complain if the file is absent.
RUN mkdir -p /home/user/.vnc \
 && touch /home/user/.vnc/passwd \
 && chmod 600 /home/user/.vnc/passwd

RUN chown -R user:user /home/user

# Startup script: bypass the kasmvncserver Perl wrapper and call Xvnc directly.
# The wrapper prompts interactively for a Kasm auth password on first start
# and bails when STDIN is closed (which it is under nohup). Xvnc binary
# accepts all flags directly. This is the pattern linuxserver/webtop uses.
RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -e' \
    'export HOME=/home/user' \
    'export DISPLAY=:1' \
    'export XDG_RUNTIME_DIR=/tmp/runtime-1000' \
    'export XDG_CONFIG_HOME=$HOME/.config' \
    'export XDG_DATA_HOME=$HOME/.local/share' \
    'export XDG_CACHE_HOME=$HOME/.cache' \
    '' \
    'pkill -f Xvnc 2>/dev/null || true' \
    'pkill -f xfce4-session 2>/dev/null || true' \
    'pkill -f dbus-daemon 2>/dev/null || true' \
    'sleep 1' \
    '' \
    'mkdir -p $XDG_RUNTIME_DIR && chmod 700 $XDG_RUNTIME_DIR' \
    'mkdir -p $XDG_DATA_HOME $XDG_CACHE_HOME' \
    '' \
    '/usr/bin/Xvnc :1 \' \
    '    -geometry 1920x1080 \' \
    '    -depth 24 \' \
    '    -websocketPort 6901 \' \
    '    -interface 0.0.0.0 \' \
    '    -SecurityTypes None \' \
    '    -DisableBasicAuth \' \
    '    -sslOnly 0 \' \
    '    -AlwaysShared \' \
    '    -rfbport -1 &' \
    'XVNC_PID=$!' \
    '' \
    'sleep 2' \
    '' \
    'dbus-launch --exit-with-session startxfce4 &' \
    '' \
    'wait $XVNC_PID' \
    > /usr/local/bin/start-desktop.sh \
 && chmod +x /usr/local/bin/start-desktop.sh

COPY --chown=user:user agent/ /home/user/agent/

USER user
WORKDIR /home/user/workspace
