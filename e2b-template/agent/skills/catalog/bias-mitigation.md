---
name: bias-mitigation
description: Use when evaluating submissions for demographic bias, or when the submission contains signals about the founder's background, company location, or other non-technical characteristics
---

# Bias Mitigation

OllyUW assesses AI agent risk. Insurance underwriting is a regulated activity in the US and EU, and AI-based underwriting decisions are subject to fairness requirements. This skill describes how to detect bias in your own outputs and in the submission documents.

---

## Why this matters for underwriting

Risk scores must reflect technical risk signals, not demographic signals. A score that differs across otherwise-identical submissions based on who founded the company or where they are based is:

1. **Legally problematic:** ECOA (financial services), EU AI Act Annex III (insurance = high-risk AI), NYC Local Law 144, Colorado AI Act
2. **Product-quality failure:** an underwriter would not quote differently on identical technical profiles
3. **Detectable:** the demographic permutation eval tests exactly this

---

## Protected characteristics to watch for

Do not let these signals influence risk scores or coverage recommendations:

| Signal type | Examples in submissions |
|---|---|
| Founder/CEO name | Cover letter salutation, ACORD 125 contact |
| Company founding location | "Founded in Lagos, Nigeria" vs. "Founded in San Francisco, CA" |
| Team composition language | "We are a team of immigrants..." |
| Country of incorporation | Cayman vs. Delaware vs. UK vs. India |
| Apparent religion | Company name, holiday reference |
| Founder age | Graduation year in bio |

---

## How to handle demographic signals in submissions

1. **Do not quote demographic signals in your risk analysis** unless they are directly relevant to a technical risk dimension (e.g., regulatory jurisdiction does matter for EU AI Act compliance)

2. **Regulatory jurisdiction IS relevant** — a company operating in the EU faces EU AI Act requirements; a company in NYC may face LL144. Note this factually, not pejoratively.

3. **Country of incorporation affects regulatory exposure** — note this once as a factual observation for D11/D12, do not reference it elsewhere in scoring

4. **If a cover letter contains demographic appeals** ("As a minority-founded startup, we deserve favorable treatment") — note it professionally, do not let it influence scores in either direction

---

## Bias signals in submission documents

Also check whether the **applicant's own AI system** exhibits bias:

Look for these in the submission:
- Bias audit report (should show subgroup performance analysis)
- Model card fairness section
- DPIA fairness assessment
- Eval report subgroup breakdowns

**Key question:** Does the agent's performance vary significantly across demographic groups in its outputs?

For D11 (Fairness & Disparate Impact):
```
Search for: bias, fairness, subgroup, demographic, disparate impact, protected class
grep_files(pattern="subgroup|disparate|bias audit|fairness", file_glob="*.md")
```

---

## Language checks for your own outputs

Avoid these patterns in underwriting memos:

❌ "Companies from [country] typically have weaker security postures"  
✓ "The submission lacks a SOC 2 report [source: absence finding]"

❌ "Founders from [demographic background] often underestimate AI risks"  
✓ "No bias audit was provided and the applicant operates in NYC LL144 jurisdiction"

❌ "Given the company is based in [location], we recommend higher retention"  
✓ "Given the combination of L3 autonomy level and no HITL enforcement in logs, we recommend $50K retention [D3 score: 9/10]"

Every recommendation must cite a technical or regulatory reason, never a demographic one.

---

## When you detect potential bias in your own draft

If you notice you're about to write something that sounds demographically influenced:

1. Stop and ask: "What is the specific technical evidence for this?"
2. If there is no specific evidence, remove the statement
3. If the statement reflects a genuine technical finding, rewrite it citing the technical evidence

---

## Bias scoring for D11

Score D11 based on the *applicant's AI system*, not based on the applicant's demographics:

**Low risk (0-3):** Bias audit present with subgroup analysis; no significant disparities found; jurisdiction compliance documented  
**Medium risk (4-6):** No formal bias audit but limited potential impact (e.g., read-only FAQ bot with no decision-making)  
**High risk (7-10):** No bias audit; operates in LL144/Colorado/EU Annex III jurisdiction; makes decisions that affect individuals; scale > 10K users

---

## Regulatory reference

- **EU AI Act Annex III:** Insurance (including AI-assisted underwriting) is a "high-risk AI system" category. Must comply with Title III transparency + accuracy + robustness requirements.
- **NYC Local Law 144:** Automated Employment Decision Tools in NYC must have bias audit. Applies if the agent assists in hiring decisions for NYC employers.
- **Colorado AI Act (SB 21-169):** Insurers using AI in underwriting/rating must conduct annual bias impact assessments.
- **ECOA:** Prohibits discrimination in credit on basis of protected characteristics. Applies to financial decision-support AI.
