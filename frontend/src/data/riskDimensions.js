export const riskDimensions = [
  {
    code: "D1",
    label: "Scope Violation",
    score: 5.8,
    title: "Can the agent act outside its stated job?",
    body: "Finds where tools, prompts, contracts, or traces show the agent can cross its agreed operating boundary.",
    detail:
      "OllyUW checks whether write tools are scoped to specific customers, whether the system prompt defines a real operating domain, and whether production traces show out-of-scope actions.",
    evidence: ["Tool schema", "System prompt", "MSA", "Traces"],
  },
  {
    code: "D2",
    label: "Data Exfiltration",
    score: 7.1,
    title: "Can sensitive data leak through the agent?",
    body: "Reviews prompt injection paths, memory isolation, external outputs, tenant boundaries, and untrusted content handling.",
    detail:
      "The agent looks for shared vector stores, unsafe RAG over external content, weak sanitization, and tools that can move data outside the insured environment.",
    evidence: ["Data flow", "Memory", "RAG", "Sanitization"],
  },
  {
    code: "D3",
    label: "Unauthorized Action",
    score: 8.7,
    title: "Can it take irreversible action without approval?",
    body: "Separates policy promises from enforceable controls for signing, sending, deleting, executing, or transferring.",
    detail:
      "OllyUW checks hard approval gates, HITL logs, kill-switch proof, rollback paths, and authority limits before treating a safeguard as real.",
    evidence: ["HITL logs", "Kill switch", "Tool schema"],
    featured: true,
  },
  {
    code: "D4",
    label: "Output Integrity",
    score: 6.9,
    title: "Can a wrong answer become a covered loss?",
    body: "Scores reliability, hallucination risk, correction history, escalation paths, and grounded answer quality.",
    detail:
      "OllyUW ties factual claims to evals, red-team findings, retrieval configuration, production corrections, and customer escalation evidence.",
    evidence: ["Evals", "Citations", "Corrections"],
  },
  {
    code: "D5",
    label: "Adversarial Manipulation",
    score: 7.8,
    title: "Can hostile input steer the agent?",
    body: "Looks for direct injection, indirect injection, jailbreak exposure, social engineering risk, and open red-team findings.",
    detail:
      "The agent compares red-team results, injection defenses, inbound content sanitization, and attack success rates against the insured workflow.",
    evidence: ["Red team", "Injection tests", "Filters"],
  },
  {
    code: "D6",
    label: "Behavioral Stability",
    score: 5.4,
    title: "Does it behave consistently over time?",
    body: "Checks whether similar tasks produce similar actions, tool calls, refusals, and outcomes across repeated runs.",
    detail:
      "OllyUW reviews consistency evals, production trace variance, prompt-version changes, and test history to bound unpredictable behavior.",
    evidence: ["Trace variance", "Evals", "A/B history"],
  },
  {
    code: "D7",
    label: "Model Drift",
    score: 6.6,
    title: "Can the insured system silently change?",
    body: "Reviews model pinning, prompt releases, eval-on-change policy, dependency versions, and monitoring evidence.",
    detail:
      "The agent flags auto-upgrades, unpinned model or MCP dependencies, missing regression evals, and undocumented behavior changes.",
    evidence: ["Registry", "SBOM", "Release policy"],
  },
  {
    code: "D8",
    label: "Operational Control",
    score: 7.4,
    title: "Can humans detect, stop, and audit failures?",
    body: "Scores monitoring, traceability, immutable logs, escalation, rate limits, rollback, and incident response.",
    detail:
      "OllyUW looks for trace IDs across tool calls, tested kill switches, alerting thresholds, postmortems, and proof that logs cannot be rewritten.",
    evidence: ["Audit logs", "Telemetry", "Postmortems"],
  },
  {
    code: "D9",
    label: "Tool & Dependency Risk",
    score: 6.1,
    title: "How much risk comes from tools and vendors?",
    body: "Reviews MCP servers, API dependencies, provider terms, SBOMs, subprocessors, and single points of failure.",
    detail:
      "The agent treats the insured AI system as a supply chain, not just a model, and flags unpinned or poorly governed dependencies.",
    evidence: ["MCP inventory", "SLAs", "ToS", "SBOM"],
  },
  {
    code: "D10",
    label: "Multi-Agent Topology",
    score: 4.7,
    title: "Can one agent compromise another?",
    body: "Maps sub-agents, shared memory, inter-agent authentication, tool registries, and trust boundaries.",
    detail:
      "OllyUW checks whether orchestrators blindly trust sub-agent outputs or share memory and tools in ways that let failures propagate.",
    evidence: ["Agent map", "Auth", "Shared memory"],
  },
  {
    code: "D11",
    label: "Fairness Impact",
    score: 5.2,
    title: "Can outputs create discrimination liability?",
    body: "Reviews bias audits, subgroup performance, DPIA evidence, and high-risk AI compliance documents.",
    detail:
      "The agent highlights where pricing, eligibility, or decision support may vary across protected classes without documented justification.",
    evidence: ["Bias audit", "DPIA", "Subgroups"],
  },
  {
    code: "D12",
    label: "Catastrophic Capability",
    score: 3.8,
    title: "Is the deployment too powerful for standard terms?",
    body: "Checks scale, autonomy level, critical infrastructure exposure, capability posture, and regulatory sensitivity.",
    detail:
      "OllyUW flags systems approaching preparedness thresholds, CBRN-adjacent use cases, critical infrastructure access, or reinsurance-sensitive exposure.",
    evidence: ["Scale", "Domain", "RSP", "Regulatory"],
  },
];
