---
name: parallel-web-research-with-subagents
description: Parallelize web research across multiple subagents (web_search only) to gather information on several topics simultaneously.
---
# Parallel Web Research with Subagents

When you need to gather information on multiple independent topics, delegate each topic to a separate subagent restricted to `web_search` only (no shell, no browser). This speeds up research and keeps results structured.

## When to Use
- You have 2+ distinct questions or targets to research.
- Each sub-task is self-contained and only needs current web info.
- You want a clean, table-formatted summary of findings.

## Pattern
1. **Define clear, independent goals** for each subagent. Keep each goal specific (e.g., "Top 3 recent AI model releases from Google, OpenAI, and Anthropic in 2024").
2. **Delegate in parallel** using the `delegate` tool (or similar multi-agent spawn). Grant only `web_search` (or `web_research`) tools — no shell or browser.
3. **Await all outputs.** The delegate tool typically blocks until all subagents finish.
4. **Format results** into a readable table, list, or summary (e.g., markdown table with columns: Model, Company, Date, Highlight).

## Example (from trajectory)
```
delegate: [
  {
    "goal": "Research and summarise the 3 biggest recent AI model releases or announcements from 2024-2025 (e.g. from OpenAI, Anthropic, Google, Meta)",
    "success": true,
    "output": "..."
  },
  {
    "goal": "Research the latest advancements in quantum computing from 2024",
    "success": true,
    "output": "..."
  }
]
```
Then present:
| Model | Company | Date | Highlight |
|-------|---------|------|-----------|
| ...   | ...     | ...  | ...       |

## Notes
- Ensure subagent goals are narrow enough to complete quickly.
- If a subagent fails, still present partial results with a note.
- Use `web_search` (or `web_research`) — never `shell` or `browser` unless required.