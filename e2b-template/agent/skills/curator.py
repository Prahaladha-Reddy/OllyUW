"""
Post-task skill curator (SkillOS pattern).

After a task completes, runs a lightweight LLM pass over the trajectory
and decides whether to insert, update, or delete any skills.
Called from agent_loop.py after every final response.
"""
from __future__ import annotations

import re
from pathlib import Path

from agent.log import log
from agent.skills.discovery import CATALOG_DIR
from agent.skills.loader import regenerate_allskills

_CURATOR_SYSTEM = """\
You are a skill curator. Your job is to decide whether the agent's trajectory
contains a reusable pattern worth saving as a skill.

A skill is a markdown file with YAML frontmatter:
---
name: kebab-case-name
description: One sentence — what this skill is for and when to use it.
---
[Markdown body: the actual guide, examples, patterns]

Respond with ONE of:
- "NO_SKILL" — if nothing reusable was learned
- "INSERT:<skill-name>" followed by the full skill markdown (frontmatter + body)
- "UPDATE:<skill-name>" followed by the updated full skill markdown
- "DELETE:<skill-name>" — if an existing skill is clearly outdated/wrong

Be conservative: only create skills for patterns the agent will definitely reuse.
Short one-off tasks → NO_SKILL.
"""


async def curate(trajectory: str, model: str = "deepseek") -> None:
    """Run the curator over a task trajectory string. Fire-and-forget."""
    try:
        await _run_curator(trajectory, model)
    except Exception as exc:
        log.warning("skill curator failed: %s", exc)


async def _run_curator(trajectory: str, model: str) -> None:
    from agent.llm.streaming import step as model_step

    messages = [
        {"role": "user", "content": f"Task trajectory:\n\n{trajectory}\n\nShould a skill be created/updated/deleted?"},
    ]
    # Use a cheap single-step call — no tool use needed.
    from agent.llm.providers import resolve, normalise_base_url
    from agent.observability.langfuse_setup import openai_module
    import time

    base_url, api_key, model_name = resolve(model)
    base_url = normalise_base_url(base_url)
    OpenAI = openai_module().OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": _CURATOR_SYSTEM},
            *messages,
        ],
        stream=False,
        max_tokens=1500,
    )
    content = response.choices[0].message.content or ""
    _apply_curator_decision(content.strip())


def _apply_curator_decision(decision: str) -> None:
    if decision.startswith("NO_SKILL"):
        return

    if decision.startswith("INSERT:") or decision.startswith("UPDATE:"):
        prefix = "INSERT:" if decision.startswith("INSERT:") else "UPDATE:"
        rest = decision[len(prefix):]
        # First line is the skill name, rest is the markdown
        lines = rest.strip().splitlines()
        skill_name = lines[0].strip()
        skill_body = "\n".join(lines[1:]).strip()
        if not skill_name or not skill_body:
            log.warning("curator returned malformed skill: %s", decision[:100])
            return
        # Ensure frontmatter has correct name
        if not skill_body.startswith("---"):
            skill_body = f"---\nname: {skill_name}\ndescription: (auto-generated)\n---\n{skill_body}"
        skill_file = CATALOG_DIR / f"{skill_name}.md"
        CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(skill_body, encoding="utf-8")
        regenerate_allskills()
        log.info("skill curator %s skill: %s", prefix.rstrip(":").lower(), skill_name)
        return

    if decision.startswith("DELETE:"):
        skill_name = decision[len("DELETE:"):].strip()
        skill_file = CATALOG_DIR / f"{skill_name}.md"
        if skill_file.exists():
            skill_file.unlink()
            regenerate_allskills()
            log.info("skill curator deleted skill: %s", skill_name)
        return

    log.debug("skill curator returned unrecognised decision: %s", decision[:80])
