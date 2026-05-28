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
  "Unlock one persistent computer instead of starting a fresh chat every time.",
  "Upload files and folders so the agent has a stable workspace to read from and write to.",
  "Connect the apps and browser sessions the agent needs to keep operating across visits.",
  "Start a goal, leave the tab, and come back to the same machine state later.",
  "Inspect the file tree, connected apps, and saved context from one control surface.",
];

export const evidenceDocumentExamples = [
  "Security reports, SOC 2 evidence, pen tests, audit logs, and incident postmortems.",
  "Tool schemas, MCP server inventories, system prompts, HITL logs, and kill-switch proof.",
  "Contracts, MSAs, privacy policies, DPAs, subprocessors, retention policies, and customer terms.",
  "Model registry records, release notes, eval results, red-team reports, bias audits, and production traces.",
  "Architecture diagrams, data-flow maps, memory/RAG design, tenant isolation proof, and SBOMs.",
];
