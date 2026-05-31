---
name: demonstrate-parallel-execution
description: When the user asks to see or demonstrate parallel tool execution, fire off multiple independent small tasks simultaneously and present the results.
---

# Demonstrate Parallel Execution

Use this skill when a user explicitly asks to see your parallel tool execution capability (e.g., "show me that you can run parallel tools", "do multiple things at once").

## Steps

1. **Select 4-6 small, independent tasks** that can run in parallel without dependencies:
   - Get current date/time (`date` / `Get-Date`)
   - Get system info (`uname -a` / `systeminfo` or OS-specific commands)
   - Get Python version and key packages (`python --version && pip list --format=columns`)
   - List workspace contents (`ls` / `dir`)
   - Perform a web search (use `web_search` tool with a fun query like "interesting fun facts")
   - Check disk space (`df -h` / `wmic logicaldisk get size,freespace`)

2. **Adapt commands to the OS** — if the environment is Windows, use `dir`, `systeminfo`, `python --version`, etc. If Linux, use `ls`, `uname -a`, etc.

3. **Fire all tool calls in a single agent response** using the correct tool names:
   - For shell commands: `run_shell` with appropriate OS-specific command.
   - For web search: `tool_call` (with tool_name='web_search' or directly if it's a core tool). Ensure correct parameters (e.g., `query`, `max_results`).

4. **Handle errors gracefully** — if some calls fail (e.g., timeout, unknown command), note the error and re-run with fixed commands. All successful results will come back.

5. **Present results in a clean summary** — aggregate the outputs of all tasks and present them in a structured way (e.g., table or bullet list with headings).

## Example Prompt

> "show me that you can run parallel tools, do any task that demonstrates"

## Example Output Style

```
✅ All N tasks ran at the same time — here's what came back:

| Task | Result |
|------|--------|
| 1. Date | 2026-05-31 22:11:15 |
| 2. Workspace | dir output... |
| 3. Python | Python 3.12.11, packages... |
| 4. System | Windows 11 Home... |
| 5. Web search | Fun facts results... |
```

## Notes

- The key is **independence** — no task should rely on the output of another.
- Use `tool_call` for deferred tools like `web_search` (first `tool_search` to confirm availability, then `tool_call` with correct args).
- If the environment is unknown, start with a safe command (e.g., `echo "test"`) to detect OS before launching parallel tasks.