"""
OllyUW E2B Sandbox Template

This file defines the baked sandbox image. Running `e2b template build` from
this directory (or calling Template.build()) produces a custom template ID.
Store that ID in E2B_TEMPLATE_ID in your .env so the backend uses it instead
of the base image.

Usage:
    cd e2b-template
    e2b template build          # CLI approach

Notes:
    The Dockerfile in this directory defines the full build process.
    The build includes agent dependencies and a desktop environment with
    VNC + noVNC for GUI streaming to the frontend.
"""
from __future__ import annotations

from pathlib import Path

from e2b import Template, default_build_logger
from dotenv import load_dotenv

TEMPLATE_NAME = "ollyuw-agent"
TEMPLATE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEMPLATE_DIR.parent


def load_env_files() -> None:
    load_dotenv(PROJECT_DIR / ".env")
    load_dotenv(TEMPLATE_DIR / ".env", override=True)


# Build from Dockerfile in this directory
# The Dockerfile installs all agent dependencies + desktop/VNC setup
load_env_files()
template = Template().from_dockerfile(str(TEMPLATE_DIR / "Dockerfile"))


if __name__ == "__main__":
    import os

    load_env_files()

    if not os.getenv("E2B_API_KEY"):
        raise SystemExit("Set E2B_API_KEY before building the template.")

    built = Template.build(
        template,
        TEMPLATE_NAME,
        cpu_count=2,
        memory_mb=2048,
        on_build_logs=default_build_logger(),
    )
    print(f"\nTemplate built: {built.template_id}")
    print(f"Add to .env:   E2B_TEMPLATE_ID={built.template_id}")
