---
name: parallel-subagent-research
description: Use parallel subagents to research multiple independent topics simultaneously and aggregate results.
---

# Parallel Subagent Research

When you need to gather information on several independent topics at once, delegate each topic to a subagent running in parallel. This pattern is ideal for:

- Comparing multiple options (languages, tools, frameworks, products, etc.)
- Fact-checking across different sources
- Collecting diverse perspectives or examples

## How to use

1. Formulate a clear, self-contained goal for each subagent. Each goal should include specific questions or deliverables (e.g., “find best resources, key strengths, use cases, and a code example”).
2. Pass an array of goal objects to the `delegate` tool. Each object must have a `goal` field (string) and optionally a `success` field (boolean).
3. After all subagents return, collect their outputs and compile them into a final answer (e.g., table, summary, comparison).

## Example (from trajectory)

```json
{
  "tool": "delegate",
  "params": [
    {
      "goal": "Research Python for beginners. Find: best learning resources, key strengths, common use cases, and a quick code example of a hello world + list comprehension."
    },
    {
      "goal": "Research Rust for systems programming. Find: best learning resources, key strengths, common use cases, and a quick code example of a hello world + a struct."
    },
    {
      "goal": "Research Go for backend/services. Find: best learning resources, key strengths, common use cases, and a quick code example of a hello world + a simple HTTP server."
    }
  ]
}
```

The subagents run in parallel, each returns its research. Then the agent synthesizes a side‑by‑side comparison table.

## When NOT to use

- The topics are interdependent (e.g., one subagent’s result is needed by another).
- The tasks require shared state or sequential context.
- The total work is tiny – parallelizing adds overhead.

## Tips

- Keep goals self‑contained and precise.
- For best results, ask each subagent to include concrete examples or code snippets.
- If you need a combined analysis, instruct subagents to format their output in a way that is easy to merge (e.g., plain text sections).

Use this pattern to leverage parallel subagents and deliver comprehensive, multi‑faceted answers quickly.