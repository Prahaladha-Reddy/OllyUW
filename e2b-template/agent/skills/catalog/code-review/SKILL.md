---
name: code-review
description: Review code for bugs, security issues, style problems, and performance. Use when asked to review a PR, check code quality, find issues, or audit a codebase.
---

# Code Review

## Workflow

1. **Discover** — use `get_file_outline` on each file first, not full reads.
2. **Read selectively** — read functions/classes that look suspicious using line ranges.
3. **Run the linter script** if available — it catches obvious issues automatically.
4. **Grade each finding**: critical / high / medium / low / info.
5. **Report** — group by severity; include file, line, exact code, and fix suggestion.

## What to check

**Bugs**
- Null/undefined dereferences
- Off-by-one errors in loops/slices
- Incorrect boolean logic
- Unhandled exceptions / error paths ignored

**Security**
- Injection (SQL, shell command, path traversal)
- Hardcoded secrets or tokens
- Insecure deserialization
- Missing input validation at system boundaries

**Performance**
- N+1 query patterns
- Unbounded loops over large data
- Missing caching for expensive operations
- Large allocations in hot paths

**Code quality**
- Functions doing too many things (> ~40 lines is a smell)
- Duplicated logic that should be extracted
- Magic numbers/strings without named constants
- Dead code, commented-out blocks

## Output format

```
## Critical
- [file.py:42] SQL injection: user input passed directly to query. Fix: use parameterised queries.

## High
- [auth.py:17] Hardcoded secret key. Fix: move to environment variable.

## Medium
- ...

## Summary
X critical, Y high, Z medium issues found.
```
