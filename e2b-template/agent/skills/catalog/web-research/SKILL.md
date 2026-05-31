---
name: web-research
description: Deep multi-source web research with synthesis and citations. Use for questions needing multiple sources, fact-checking, or comprehensive summaries of a topic.
---

# Web Research

## When to use what

- `web_search(query)` — quick lookup, one question, fast (use tool_search to find it)
- `web_research(question)` — deep synthesis across sources, 30-90s, cited (use tool_search to find it)

For simple factual questions, `web_search` is enough.
For complex research tasks, use `web_research` then cross-reference key claims.

## Workflow for comprehensive research

1. **Decompose** the question into 3-5 sub-questions.
2. Run `web_search` for each sub-question **in parallel** (single response, multiple tool calls).
3. Synthesise the results. Note any contradictions.
4. For claims that are critical or disputed, run `web_research` to get cited synthesis.
5. Produce a structured report with inline citations.

## Citation format

Always cite sources inline:
> According to [Source Name](url), "direct quote here."

Never state a fact from web results without attributing it.

## Handling contradictions

When sources disagree:
1. Note the disagreement explicitly: "Sources differ on X: [A] says ... while [B] says ..."
2. Indicate which is more credible (recency, authority, primary vs secondary source).
3. Do not silently pick one version.

## Anti-patterns to avoid

- Do NOT use `web_research` for every question — it's slow and expensive.
- Do NOT summarise search results without citing them.
- Do NOT hallucinate details not present in the sources.
- Do NOT pass more than one compound question to `web_research` — split them up.
