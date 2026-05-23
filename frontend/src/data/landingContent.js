export const comparisonRows = [
  {
    step: "Read the evidence",
    manual: "Underwriters jump between PDFs, contracts, SOC 2 reports, policies, diagrams, logs, and spreadsheets.",
    olly: "OllyUW ingests the full package and turns it into one searchable underwriting file.",
  },
  {
    step: "Find contradictions",
    manual: "Claims are checked by memory and notes: privacy promises, approval controls, model versions, and tool access.",
    olly: "OllyUW cross-checks the same claim across documents and flags conflicts with source citations.",
  },
  {
    step: "Turn risk into terms",
    manual: "The underwriter manually connects technical gaps to subjectivities, exclusions, limits, and retentions.",
    olly: "OllyUW maps each finding to the underwriting position it supports, then drafts the memo.",
  },
  {
    step: "Answer follow-ups",
    manual: "A new question means reopening the file and rebuilding the reasoning from scattered notes.",
    olly: "Ask why a score is high, what source supports an exclusion, or what evidence would improve the quote.",
  },
];

export const workflowSteps = [
  "Bring in the full evidence package: security reports, contracts, architecture diagrams, control proof, logs, policies, and prior incidents.",
  "OllyUW reads across the file, extracts underwriting signals, and organizes the evidence into a reviewable workspace.",
  "Contradictions rise to the top: privacy promises that do not match architecture, approval gaps, unsupported accuracy claims, and missing control proof.",
  "Draft a source-backed underwriting memo with risk findings, subjectivities, recommended terms, exclusions, and paths to coverage.",
  "Interrogate the underwriting file after the memo is drafted: ask why a score moved, which source supports an exclusion, or what evidence would improve the terms.",
];

export const evidenceDocumentExamples = [
  "Security reports, SOC 2 evidence, pen tests, audit logs, and incident postmortems.",
  "Tool schemas, MCP server inventories, system prompts, HITL logs, and kill-switch proof.",
  "Contracts, MSAs, privacy policies, DPAs, subprocessors, retention policies, and customer terms.",
  "Model registry records, release notes, eval results, red-team reports, bias audits, and production traces.",
  "Architecture diagrams, data-flow maps, memory/RAG design, tenant isolation proof, and SBOMs.",
];
