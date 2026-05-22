"""
OllyUW E2B Sandbox Template

This file defines the baked sandbox image. Running `e2b template build` from
this directory (or calling Template.build()) produces a custom template ID.
Store that ID in E2B_TEMPLATE_ID in your .env so the backend uses it instead
of the base image.

Usage:
    cd e2b-template
    e2b template build          # CLI approach
    # — or —
    python template.py          # programmatic build (requires E2B_API_KEY)
"""
from __future__ import annotations

from pathlib import Path

from e2b import Template, default_build_logger
from dotenv import load_dotenv
load_dotenv()
TEMPLATE_NAME = "ollyuw-agent"
TEMPLATE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEMPLATE_DIR.parent


def load_env_files() -> None:
    load_dotenv(PROJECT_DIR / ".env")
    load_dotenv(TEMPLATE_DIR / ".env", override=True)

template = (
    Template()
    .from_base_image()
    # Pre-install all agent dependencies so sandboxes start instantly.
    # The worker code itself is uploaded at session-creation time so you can
    # update agent logic without rebuilding the template.
    .pip_install(
        [
            "redis>=5.0.0",
            "langchain-openai>=1.2.0",
            "langchain-core>=0.3.0",
            "python-dotenv>=1.0.1",
        ]
    )
    # Common system utilities the agent might need in run_shell calls.
    .apt_install(["curl", "git", "jq"])
)


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
