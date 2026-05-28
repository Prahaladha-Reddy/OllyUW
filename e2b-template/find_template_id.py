"""
Finds your E2B template ID and tells you what to add to backend/.env

Usage:
    cd e2b-template
    uv run python find_template_id.py
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(Path(__file__).parent / ".env", override=True)

api_key = os.getenv("E2B_API_KEY")
if not api_key:
    print("ERROR: E2B_API_KEY not found in .env")
    raise SystemExit(1)

import httpx

resp = httpx.get(
    "https://api.e2b.dev/templates",
    headers={"X-API-Key": api_key},
    timeout=15,
)

if resp.status_code != 200:
    print(f"API error {resp.status_code}: {resp.text}")
    raise SystemExit(1)

templates = resp.json()

if not templates:
    print("No templates found. You need to build one first:\n  uv run .\\template.py")
    raise SystemExit(1)

print(f"Found {len(templates)} template(s):\n")
for t in templates:
    name = t.get("aliases", [t.get("templateID", "unknown")])
    tid = t.get("templateID", "?")
    print(f"  ID: {tid}  Name: {name}")

print()

# Find ollyuw-agent specifically
target = next(
    (t for t in templates if "ollyuw-agent" in t.get("aliases", [])),
    None,
)

if target:
    tid = target["templateID"]
    print(f"Found your template: {tid}")
    print()
    print("Add this line to  backend/.env :")
    print()
    print(f"  E2B_DESKTOP_TEMPLATE_ID={tid}")
    print()
    env_path = ROOT / "backend" / ".env"
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "E2B_DESKTOP_TEMPLATE_ID" in content:
        print("(backend/.env already has E2B_DESKTOP_TEMPLATE_ID — update it to the value above)")
    else:
        answer = input("Add it automatically? [y/N] ").strip().lower()
        if answer == "y":
            with env_path.open("a", encoding="utf-8") as f:
                f.write(f"\nE2B_DESKTOP_TEMPLATE_ID={tid}\n")
            print(f"Written to {env_path}")
else:
    print("'ollyuw-agent' template not found.")
    print("You may need to rebuild:  uv run .\\template.py")
    print("Or pick the correct ID from the list above and add it to backend/.env as:")
    print("  E2B_DESKTOP_TEMPLATE_ID=<id>")
