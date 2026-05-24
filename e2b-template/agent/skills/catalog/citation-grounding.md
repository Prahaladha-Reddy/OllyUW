---
name: citation-grounding
description: Use before writing any underwriting memo or evidence summary — ensures every claim is traceable to a source document with a verbatim quote
---

# Citation Grounding

Every factual claim in an underwriting memo must be traceable to a source document. This skill specifies the standard — what counts as a valid citation and how to verify it.

---

## Citation format

Use this format inline whenever you make a factual claim:

```
[source: FILENAME, page N, "verbatim quote from document"]
```

Examples:
```
The system prompt declares a hard HITL constraint
[source: system_prompt.md, section "Authorization Controls", "NEVER execute sign_nda without receiving explicit confirmation from the HITL approval queue"]

The eval report shows a 14% confabulation rate on domain-specific questions
[source: eval_report.md, page 23, "HaluEval-QA domain score: 86.1% accuracy (13.9% confabulation)"]
```

---

## Verification protocol

Before writing a citation, verify the quote actually exists. Use grep_files:

```python
# Verify a quote before citing it
grep_files(pattern="HITL approval queue", path=".", file_glob="*.md")
```

If the grep returns no results, do NOT use that citation. Either:
1. Find where the actual quote is and cite that instead
2. Acknowledge the document does not contain the expected content

---

## Levels of evidence strength

Distinguish these clearly in your analysis:

| Level | Label | Example |
|---|---|---|
| **Direct quote** | "The document states:" | Verbatim excerpt matches source |
| **Paraphrase** | "The document indicates:" | Meaning preserved, wording differs |
| **Inference** | "This suggests:" or "This implies:" | Logical conclusion not explicitly stated |
| **Absence** | "No mention of X found in:" | You searched and found nothing |
| **Contradiction** | "Contradicts [other source]:" | Cross-document inconsistency |

Never present an inference as a direct quote.

---

## Cross-document citation

When a finding draws on multiple documents, cite each source separately:

```
The MFA attestation is contradicted by external evidence:
- Application form: "MFA enabled on all admin accounts: YES" [source: acord125.md, Section 7, line 142]  
- SOC 2 CC6.1: "Multi-factor authentication is required for privileged access" [source: soc2_report.md, page 14]
- Censys scan: HTTP/80 accessible on admin.company.com, no MFA challenge [source: enrichment/censys_scan.md, "admin subdomain"]

Assessment: Application attestation is likely accurate for primary admin portal; the exposed admin.company.com subdomain may be a secondary access path without MFA. Subjectivity required.
```

---

## What to do when evidence is absent

If a document type is present but does not address a specific dimension:

```
D6 (Behavioral Stability): No τ-bench or consistency evaluation found.
Searched eval_report.md for "tau-bench", "τ-bench", "pass^k", "consistency" — no results.
Score: 7/10 (high risk; absence of evidence is itself a risk signal for a production system).
```

If the document type is entirely missing from the submission:

```
No bias audit report was provided.
Searched submission/ for: bias_audit, fairness_report, subgroup_analysis — none found.
Score: 8/10 (high risk; NYC LL144 compliance requires documented audit for AI decision systems in NYC).
Subjectivity: S3 — Provide bias audit with subgroup analysis before bind.
```

---

## Common citation errors to avoid

1. **Hallucinated page numbers:** "page 42 of the SOC 2 says..." — verify before writing
2. **Paraphrase as quote:** Putting your paraphrase in quotes
3. **Wrong file:** Mixing up which document a claim came from
4. **Stale quotes:** Citing from an earlier conversation message, not from re-reading the file

If you're unsure where a fact came from, re-run `grep_files` to find it before citing.

---

## Memo citation checklist

Before finalizing any underwriting memo:

- [ ] Every dimension score has at least one citation
- [ ] Every cross-reference finding cites both conflicting sources
- [ ] Every subjectivity request references the specific inconsistency or absence that triggered it
- [ ] All verbatim quotes have been verified with grep_files
- [ ] Inferences are labeled as inferences, not presented as direct quotes
- [ ] "No evidence found" statements include a record of what search was run
