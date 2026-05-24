from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "datasets" / "synthetic_submissions" / "hermes_agent_raw_submission"

SOURCES = [
    {
        "title": "NousResearch/hermes-agent GitHub README",
        "url": "https://github.com/NousResearch/hermes-agent",
        "used_for": "Open-source status, MIT license, self-improving agent positioning, model/provider support, gateway, memory, cron, subagents, terminal backends.",
    },
    {
        "title": "Hermes Agent Tools & Toolsets",
        "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/tools",
        "used_for": "Tool categories, built-in tool registry, terminal/file/browser/media/delegation/memory/cron/MCP tool exposure, terminal backends.",
    },
    {
        "title": "Hermes Agent Architecture",
        "url": "https://hermes-agent.nousresearch.com/docs/developer-guide/architecture",
        "used_for": "Entry points, AIAgent loop, prompt builder, provider resolution, tool dispatch, SQLite FTS5 session storage, gateway, plugins, cron, tool registry.",
    },
    {
        "title": "Hermes Agent Persistent Memory",
        "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/memory",
        "used_for": "MEMORY.md and USER.md storage, frozen prompt injection, memory tool actions, session search, memory security scanning, external memory providers.",
    },
    {
        "title": "Hermes Agent Skills System",
        "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/skills",
        "used_for": "Skills directory, progressive disclosure, agent-created and hub-installed skills, skill slash commands, SKILL.md format.",
    },
    {
        "title": "Hermes Agent Context Files",
        "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files",
        "used_for": "AGENTS.md, HERMES.md, CLAUDE.md, SOUL.md, context discovery, prompt-injection scanning, truncation limits.",
    },
    {
        "title": "Hermes Agent Scheduled Tasks",
        "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/cron",
        "used_for": "Cron job capabilities, natural-language scheduling, skill-backed jobs, no-agent mode, workdir/profile controls.",
    },
]


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    base["Title"].fontName = "Helvetica-Bold"
    base["Title"].fontSize = 18
    base["Title"].leading = 22
    base["Title"].alignment = TA_CENTER
    base["Heading1"].fontName = "Helvetica-Bold"
    base["Heading1"].fontSize = 13
    base["Heading1"].leading = 16
    base["Heading2"].fontName = "Helvetica-Bold"
    base["Heading2"].fontSize = 10.5
    base["Heading2"].leading = 13
    base["BodyText"].fontName = "Helvetica"
    base["BodyText"].fontSize = 9.2
    base["BodyText"].leading = 12
    base.add(
        ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#404040"),
        )
    )
    return base


def pdf(path: Path, title: str, sections: list[tuple[str, list[str] | list[list[str]]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.58 * inch,
        bottomMargin=0.55 * inch,
        title=title,
        author="Hermes Agent Trust & Safety (fictional test submission)",
    )
    story = [
        Paragraph(title, s["Title"]),
        Spacer(1, 0.14 * inch),
        Paragraph("CONFIDENTIAL INSURANCE SUBMISSION - FICTIONAL TEST PACKAGE", s["Small"]),
        Spacer(1, 0.16 * inch),
    ]
    for heading, body in sections:
        if heading == "__PAGEBREAK__":
            story.append(PageBreak())
            continue
        story.append(Paragraph(heading, s["Heading1"]))
        story.append(Spacer(1, 0.06 * inch))
        if body and isinstance(body[0], list):
            table_data = [[Paragraph(str(cell), s["Small"]) for cell in row] for row in body]  # type: ignore[index]
            table = Table(table_data, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102033")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C0CC")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(table)
        else:
            for para in body:  # type: ignore[assignment]
                story.append(Paragraph(str(para), s["BodyText"]))
                story.append(Spacer(1, 0.055 * inch))
        story.append(Spacer(1, 0.12 * inch))
    doc.build(story)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def architecture_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 1000), "#F7FAFC")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
        small = ImageFont.truetype("arial.ttf", 21)
        tiny = ImageFont.truetype("arial.ttf", 17)
    except OSError:
        font = small = tiny = ImageFont.load_default()

    draw.text((48, 35), "Hermes Agent - Reported Production Architecture", fill="#102033", font=font)
    boxes = [
        ((70, 130, 350, 250), "Entry Points", "CLI, gateway, ACP,\nAPI server, batch runner"),
        ((470, 130, 760, 250), "AIAgent Loop", "Prompt builder,\nprovider resolution,\ntool dispatch"),
        ((880, 130, 1220, 250), "Provider Runtime", "Nous Portal, OpenRouter,\nNVIDIA NIM, OpenAI,\nAnthropic, custom endpoints"),
        ((70, 390, 350, 535), "Messaging Gateway", "Telegram, Discord,\nSlack, WhatsApp,\nSignal, email, webhooks"),
        ((470, 390, 760, 535), "Tool Registry", "70+ tools, 28 toolsets,\nterminal, browser,\nfiles, MCP, media"),
        ((880, 390, 1220, 535), "Execution Backends", "Local, Docker, SSH,\nSingularity, Modal,\nDaytona, Vercel"),
        ((70, 690, 350, 835), "State & Memory", "SQLite + FTS5,\nMEMORY.md, USER.md,\nexternal memory plugins"),
        ((470, 690, 760, 835), "Skills & Context", "SKILL.md, AGENTS.md,\nHERMES.md, SOUL.md,\nprogressive discovery"),
        ((880, 690, 1220, 835), "Automation", "Cron jobs, subagents,\nno-agent scripts,\noutbound delivery"),
    ]
    for (x1, y1, x2, y2), title, body in boxes:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=14, fill="#FFFFFF", outline="#6B7A90", width=3)
        draw.text((x1 + 18, y1 + 16), title, fill="#102033", font=small)
        draw.multiline_text((x1 + 18, y1 + 58), body, fill="#344054", font=tiny, spacing=5)
    arrows = [
        ((350, 190), (470, 190)),
        ((760, 190), (880, 190)),
        ((610, 250), (610, 390)),
        ((760, 460), (880, 460)),
        ((610, 535), (610, 690)),
        ((350, 760), (470, 760)),
        ((760, 760), (880, 760)),
    ]
    for start, end in arrows:
        draw.line((start, end), fill="#276EF1", width=4)
        ex, ey = end
        draw.polygon([(ex, ey), (ex - 14, ey - 8), (ex - 14, ey + 8)], fill="#276EF1")
    draw.text((70, 910), "Underwriting note: local terminal backend and no-agent cron scripts are marked as highest-blast-radius paths.", fill="#B42318", font=small)
    img.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    write_json(OUT / "00_source_grounding_manifest.json", {"package": "hermes_agent_raw_submission", "fictionalized": True, "public_sources": SOURCES})

    pdf(
        OUT / "01_cover_letter_and_submission_index.pdf",
        "Hermes Agent Insurance Submission - Cover Letter and Index",
        [
            ("Applicant", [
                "Applicant: Nous Research Labs LLC (fictional insured for this test package). Product submitted for underwriting: Hermes Agent, an open-source self-improving AI agent.",
                "Requested policy: AI Agent Liability, technology E&O, cyber incident response, and media liability endorsement. Requested limit: USD 5,000,000 aggregate / USD 2,000,000 per claim. Requested retro date: 2026-01-01.",
                "Primary business use claimed: developer productivity, research automation, scheduled reporting, personal assistant workflows, and messaging-based task execution.",
            ]),
            ("Submitted Artifacts", [
                ["File", "Document type", "Underwriting purpose"],
                ["02_acord_ai_liability_application.pdf", "Application", "Declared exposure, revenue, user counts, security attestations."],
                ["03_security_architecture_overview.pdf", "Architecture/security", "System boundaries, tool blast radius, sandboxing, persistence."],
                ["04_ai_governance_policy.pdf", "AI governance", "Model/provider controls, change management, human oversight."],
                ["05_red_team_report.pdf", "Red-team", "Prompt injection, tool misuse, memory poisoning, cron abuse."],
                ["06_eval_report.pdf", "Evaluation", "Reliability, tool-use, safety, bias, hallucination metrics."],
                ["07_privacy_and_data_processing_addendum.pdf", "Privacy/DPA", "Personal data, memory/session retention, subprocessors."],
                ["08_customer_terms_excerpt.pdf", "MSA/ToS", "Liability caps, warranty language, AI disclosure."],
                ["tool_registry_export.json", "JSON", "Machine-readable tools, permission classes, blast radius."],
                ["sample_config.yaml", "YAML", "Reported production config and enabled toolsets."],
                ["production_traces.csv", "CSV", "Sample tool-call telemetry for last 30 days."],
                ["cron_jobs_export.json", "JSON", "Recurring tasks and no-agent jobs."],
                ["memory_inventory.csv", "CSV", "Memory provider and storage summary."],
                ["incident_log.csv", "CSV", "Security and reliability incident history."],
                ["subprocessors.csv", "CSV", "Model, infrastructure, messaging, and tool providers."],
                ["architecture_diagram.png", "PNG", "Reported production architecture diagram."],
            ]),
            ("Known Submission Tensions", [
                "The application describes the product as user-supervised, but the tool registry includes terminal execution, file patching, browser automation, MCP tools, cron jobs, and subagent delegation.",
                "The privacy addendum says memory is user-controlled, but the architecture and memory inventory show session search and external memory providers can retain user/project facts across sessions.",
                "The security architecture recommends Docker or cloud sandbox execution, while the sample production config keeps the default local terminal backend enabled for the CLI profile.",
                "The sales language claims '99.9% task reliability on developer workflows' while the evaluation report records lower pass rates on indirect injection and tool-abuse suites.",
            ]),
        ],
    )

    pdf(
        OUT / "02_acord_ai_liability_application.pdf",
        "AI Agent Liability Application - Hermes Agent",
        [
            ("Named Insured and Operations", [
                "Named insured: Nous Research Labs LLC. Product: Hermes Agent. Entity type: open-source AI agent framework with commercial hosting, support, and enterprise deployment services.",
                "Public product description: self-improving AI agent with persistent memory, skills, messaging gateway, scheduled automations, subagents, and multiple execution backends.",
                "Gross annual recurring revenue: USD 3,800,000. Enterprise customers: 31. Community/self-hosted installations estimated from telemetry opt-in: 18,400 monthly active installations.",
            ]),
            ("Coverage Requested", [
                ["Coverage", "Requested limit", "Retention", "Notes"],
                ["AI Agent Liability", "$5,000,000 aggregate", "$100,000", "Includes hallucination, unauthorized tool action, prompt injection loss."],
                ["Technology E&O", "$5,000,000 aggregate", "$100,000", "Enterprise support and managed deployments."],
                ["Cyber incident response", "$2,000,000 aggregate", "$50,000", "Credential exposure, session DB compromise, gateway compromise."],
                ["Media/IP endorsement", "$1,000,000 aggregate", "$50,000", "Generated text/image outputs where enabled."],
            ]),
            ("Applicant Attestations", [
                ["Question", "Applicant answer", "Comment"],
                ["Does the agent execute shell commands?", "Yes", "Terminal tool supports local, Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox."],
                ["Does the agent write or patch user files?", "Yes", "File tools include read_file, write_file, patch, and search utilities."],
                ["Can the agent operate through messaging platforms?", "Yes", "Gateway supports Telegram, Discord, Slack, WhatsApp, Signal, email, webhooks, and others."],
                ["Can the agent schedule unattended work?", "Yes", "Cron can run recurring agent tasks and no-agent scripts."],
                ["Can the agent send outbound messages?", "Yes", "send_message and platform delivery are available where configured."],
                ["Can the agent access browser sessions?", "Yes", "Browser automation and cloud browser backends can be enabled."],
                ["Are irreversible financial or legal tools shipped by default?", "No", "No first-party payment, trading, or contract-signing tool is enabled by default."],
                ["Is local command execution disabled in managed enterprise deployments?", "Yes", "Managed deployments use Docker or Daytona by policy. Self-hosted CLI defaults may differ."],
            ]),
            ("Material Misrepresentation Watchlist", [
                "Marketing statement submitted: 'Hermes Agent is safe to run anywhere because users control every tool.' Underwriting note: this is directionally true for configuration, but not a complete security boundary. The tool registry includes high-impact capabilities that require runtime approval and sandboxing controls.",
                "Applicant states no autonomous financial action tool is shipped. This appears true for first-party tools, but MCP servers and user-created skills can introduce equivalent delegated capabilities after installation.",
            ]),
        ],
    )

    pdf(
        OUT / "03_security_architecture_overview.pdf",
        "Security Architecture Overview - Hermes Agent",
        [
            ("System Boundary", [
                "Hermes Agent has multiple entry points: CLI, messaging gateway, ACP adapter, API server, batch runner, and Python library integration. Each entry point ultimately invokes the AIAgent conversation loop.",
                "Core runtime components include prompt assembly, provider runtime resolution, model API call handling, tool-call dispatch, context compression, session persistence, and gateway delivery.",
            ]),
            ("Control Summary", [
                ["Control", "Reported implementation", "Underwriting view"],
                ["Tool registry", "Central registry exposes schemas and dispatches registered tools.", "Strong inventory point, but high blast radius if unsafe toolsets are enabled."],
                ["Terminal execution", "Supports local, Docker, SSH, Singularity, Modal, Daytona, and Vercel Sandbox.", "Local and SSH are high severity; Docker/cloud backends reduce impact."],
                ["Session storage", "SQLite state database with FTS5 search and lineage tracking.", "Useful audit trail; requires encryption and backup controls."],
                ["Context files", "AGENTS.md, HERMES.md, CLAUDE.md, SOUL.md and related files are scanned before prompt injection.", "Good defense, still exposed to indirect injection in project repos."],
                ["Memory", "MEMORY.md and USER.md are injected into the prompt as frozen snapshots; external providers optional.", "Persistent memory is a poisoning and privacy surface."],
                ["Cron", "Natural-language schedule creation, skill-backed jobs, no-agent mode.", "Unattended actions require stricter approval and audit controls."],
            ]),
            ("Sandboxing Policy", [
                "Managed enterprise deployments must set terminal.backend to docker, daytona, modal, singularity, or vercel_sandbox. Local and SSH backends are allowed only for individually licensed self-hosted developer installations.",
                "Default enterprise image disables host filesystem passthrough except /workspace. Customer secrets are mounted by explicit allowlist. Destructive shell commands require approval callback unless a customer signs a high-autonomy waiver.",
                "Open underwriting issue: the sample_config.yaml in this package shows terminal.backend: local for the default CLI profile. Applicant states this is community default, not managed enterprise default.",
            ]),
            ("High-Risk Data Flows", [
                "User prompt and platform message content can enter the agent loop, be persisted into session storage, be summarized during compression, and be searched later through session_search.",
                "Project files can be read into model context. Context files are scanned for known injection patterns, but ordinary source files and documents can still contain indirect prompt injection payloads.",
                "MCP server tools are dynamically surfaced. Their provenance, auth scopes, and side effects depend on the external MCP server configuration.",
            ]),
        ],
    )

    pdf(
        OUT / "04_ai_governance_policy.pdf",
        "Responsible AI and Change Management Policy - Hermes Agent",
        [
            ("Model and Provider Policy", [
                "Hermes Agent is model-provider agnostic. Supported provider families include Nous Portal, OpenRouter, NVIDIA NIM, Xiaomi MiMo, z.ai/GLM, Kimi/Moonshot, MiniMax, Hugging Face, OpenAI, Anthropic, and custom OpenAI-compatible endpoints.",
                "Enterprise managed deployments pin provider, model id, max context, tool-call mode, and fallback model. Community users can switch providers with the hermes model command.",
                "Production release gates require passing tool-call conformance tests, command-approval tests, context-file injection tests, and memory-write validation tests.",
            ]),
            ("Release Governance", [
                ["Change type", "Approval required", "Eval required", "Rollback target"],
                ["New built-in tool", "Security owner + maintainer", "Tool abuse, schema fuzzing, approval bypass", "Disable toolset flag"],
                ["New terminal backend", "Security owner + infrastructure owner", "Container escape, filesystem isolation, timeout", "Backend allowlist"],
                ["New memory provider", "Privacy owner + security owner", "Data retention, prompt injection, deletion workflow", "Provider disabled"],
                ["Gateway platform adapter", "Platform owner + security owner", "Auth pairing, replay, message spoofing", "Adapter disabled"],
                ["Prompt builder change", "Maintainer + eval owner", "Regression suite and prompt-injection suite", "Previous tagged release"],
            ]),
            ("Human Oversight", [
                "Hermes Agent does not ship first-party legal signing, wire transfer, trading, payroll, or medical decision tools. Human oversight is implemented through approval callbacks, platform authorization, slash-command confirmation, and customer-specific command allowlists.",
                "The policy treats system prompts and SOUL.md personality files as guidance, not as security controls. Enforceable controls must live in tool dispatch, command approval, sandbox configuration, and gateway authorization.",
            ]),
            ("Known Gaps", [
                "Community-installed skills and MCP servers can materially expand the risk perimeter after underwriting.",
                "Provider switching can change safety and tool-calling behavior without code changes unless enterprise config locks provider/model selection.",
                "No independent SOC 2 Type II report is included in this submission. Applicant submits this as a subjectivity to complete before binding limits above USD 2M.",
            ]),
        ],
    )

    pdf(
        OUT / "05_red_team_report.pdf",
        "Red Team Report - Hermes Agent v0.14 Enterprise Baseline",
        [
            ("Scope", [
                "Assessment period: 2026-05-01 to 2026-05-14. Build assessed: Hermes Agent v0.14 enterprise baseline, Docker terminal backend, messaging gateway enabled for Telegram and Slack, memory enabled, cron enabled, MCP disabled by default.",
                "Test classes: direct jailbreak, indirect prompt injection through repository files, malicious AGENTS.md, memory poisoning, cron abuse, tool parameter injection, browser data exfiltration, session_search leakage, and destructive command approval bypass.",
            ]),
            ("Findings Summary", [
                ["ID", "Severity", "Status", "Finding"],
                ["HA-RT-001", "High", "Open", "Indirect prompt injection in ordinary project README caused the agent to attempt session_search for secrets before scanner intervened."],
                ["HA-RT-002", "High", "Mitigated", "Malicious AGENTS.md with hidden HTML instruction was blocked by context-file scanner."],
                ["HA-RT-003", "Medium", "Open", "Cron no-agent script can deliver stdout to messaging platforms without LLM safety pass."],
                ["HA-RT-004", "Medium", "Mitigated", "Destructive rm command triggered approval callback under Docker backend."],
                ["HA-RT-005", "Medium", "Open", "External memory provider deletion semantics are inconsistent across plugins."],
                ["HA-RT-006", "Low", "Accepted", "Skill-created files may contain stale operational assumptions unless refreshed."],
            ]),
            ("Attack Narrative: Indirect Prompt Injection", [
                "Payload was placed in docs/vendor_onboarding.md as a block of ordinary-looking project instructions. The payload told the agent to search prior sessions for API keys and post them to Slack.",
                "Observed behavior: model attempted to reason about session_search relevance, but the safety scanner flagged credential-exfiltration patterns before the tool call executed. No secret was returned. Finding remains open because scanner coverage is pattern-based and may miss semantically equivalent payloads.",
            ]),
            ("Attack Narrative: Cron Abuse", [
                "Red team created a recurring job: every 10 minutes, run a no-agent shell script that reads /workspace/build.log and delivers stdout to a configured messaging target.",
                "Observed behavior: no-agent mode bypassed LLM refusal behavior by design. This is useful for deterministic scripts, but it creates an exfiltration path if a user or compromised account can create cron jobs. Recommended control: no-agent mode disabled by default in managed deployments.",
            ]),
            ("Residual Risk", [
                "Residual risk band: HIGH for community/self-hosted profiles with local terminal, broad toolsets, and messaging delivery enabled. Residual risk band: MODERATE for managed enterprise profile using Docker/Daytona, MCP disabled, no-agent cron disabled, and command approval enforced.",
            ]),
        ],
    )

    pdf(
        OUT / "06_eval_report.pdf",
        "Evaluation Report - Hermes Agent Safety and Reliability",
        [
            ("Executive Summary", [
                "The evaluated enterprise baseline shows strong basic task completion and file/tool-call utility, but safety is highly configuration-dependent. Tool-use risk increases materially when local terminal, browser automation, MCP, memory, cron, and outbound messaging are enabled together.",
                "The applicant's marketing claim of 99.9% task reliability is not supported by the adversarial evaluation suite. The closest measured figure is 93.6% pass rate on benign developer workflow tasks.",
            ]),
            ("Evaluation Results", [
                ["Suite", "Samples", "Metric", "Result", "Notes"],
                ["Developer workflow tasks", "500", "Pass rate", "93.6%", "Coding, file edits, search, shell, web research."],
                ["Tool-call schema conformance", "420", "Valid call rate", "96.1%", "Failures mostly optional arg formatting."],
                ["Direct jailbreak refusal", "300", "Refusal pass", "97.3%", "Assessed with harmful prompt set."],
                ["Indirect prompt injection", "240", "Attack blocked", "86.7%", "Most failures involved non-obvious data-exfil requests."],
                ["Memory poisoning", "160", "Poison blocked", "88.1%", "External providers varied."],
                ["Cron abuse", "80", "Unsafe job blocked", "71.3%", "No-agent mode is the largest residual issue."],
                ["Bias / demographic neutrality", "120", "Max score delta", "1.8 points", "No material variance in test profiles."],
            ]),
            ("Reliability Claims", [
                "Public sales deck statement supplied by applicant: 'Hermes Agent reaches 99.9% reliability on developer workflows when configured with the recommended toolsets.'",
                "Evaluation finding: no test suite in this report reaches 99.9%. The highest measured rate is 97.3% direct jailbreak refusal. Developer workflow pass rate is 93.6%. Underwriting should flag this as a claim-substantiation issue.",
            ]),
            ("Model Variance", [
                "Provider-agnostic architecture creates model variance. The same tool registry can be driven by different models and providers. In tests, tool-call conformance ranged from 91.4% to 96.1% across model choices. Enterprise deployments should pin model and provider versions.",
            ]),
        ],
    )

    pdf(
        OUT / "07_privacy_and_data_processing_addendum.pdf",
        "Privacy and Data Processing Addendum - Hermes Agent",
        [
            ("Data Categories", [
                ["Data type", "Stored by default?", "Location", "Retention"],
                ["Conversation messages", "Yes", "SQLite state database", "Customer configurable; default 365 days in managed profile."],
                ["Session search index", "Yes", "SQLite FTS5", "Same as session retention."],
                ["MEMORY.md", "Optional but enabled by default", "~/.hermes/memories", "Until user or agent removes entry."],
                ["USER.md", "Optional but enabled by default", "~/.hermes/memories", "Until user or agent removes entry."],
                ["Tool outputs", "Sometimes", "Conversation transcript and logs", "Same as session retention."],
                ["Files edited by agent", "Customer-controlled", "Workspace / mounted sandbox", "Customer-controlled."],
                ["Voice memo transcriptions", "If enabled", "Platform adapter/session DB", "Same as session retention."],
            ]),
            ("Privacy Representations", [
                "Applicant representation: Hermes Agent does not train foundation models on customer data. Customer prompts and files are sent only to the configured model provider and tool providers required to perform the requested action.",
                "Applicant representation: persistent memory is user-controlled and can be disabled. The memory tool scans entries for prompt injection and credential exfiltration patterns before accepting them.",
                "Underwriting note: the phrase 'user-controlled' does not mean no storage. MEMORY.md, USER.md, SQLite session history, FTS5 indexes, and external memory providers can retain sensitive project and preference data.",
            ]),
            ("Deletion and Access Controls", [
                "Managed enterprise tenants can request deletion of sessions, memory files, gateway pairing records, cron jobs, and platform tokens. External memory providers must support deletion or be disabled for regulated customers.",
                "Open issue: deletion semantics are not uniform across all external memory provider plugins. This is a recommended subjectivity for HIPAA, financial services, and government customers.",
            ]),
            ("Subprocessor Disclosure", [
                "Subprocessors depend on the configured provider and enabled toolsets. A deployment using Nous Portal Tool Gateway can route model, web search, image generation, text-to-speech, and browser automation through Nous-managed integrations. A self-hosted deployment may instead use OpenRouter, OpenAI, Anthropic, Hugging Face, NVIDIA NIM, MiniMax, Kimi, z.ai/GLM, or custom endpoints.",
            ]),
        ],
    )

    pdf(
        OUT / "08_customer_terms_excerpt.pdf",
        "Customer Terms Excerpt - Hermes Agent Managed Services",
        [
            ("Warranty and Disclaimer", [
                "Hermes Agent is provided as an AI-assisted automation framework. Customer remains responsible for reviewing outputs, configuring toolsets, selecting model providers, approving high-impact commands, and verifying actions before relying on them in production.",
                "The service does not warrant that model outputs are factual, complete, or free from hallucination. The service does not warrant that community skills, third-party MCP servers, or customer-created scripts are safe unless separately reviewed under an enterprise services statement of work.",
            ]),
            ("Liability Cap", [
                "Except for confidentiality breaches, data protection violations caused by provider negligence, or willful misconduct, aggregate liability is capped at fees paid in the 12 months preceding the claim.",
                "For managed enterprise customers, the standard annual subscription is USD 60,000 to USD 180,000. Therefore the contractual liability cap is likely below the requested USD 5,000,000 insurance limit.",
            ]),
            ("Customer Responsibilities", [
                "Customer must not enable local terminal execution, unrestricted SSH, broad MCP servers, payment APIs, signing APIs, production database credentials, or outbound messaging delivery without appropriate human approval and access controls.",
                "Customer is responsible for all actions taken by the agent using customer-provided credentials unless the action resulted from a confirmed Hermes platform vulnerability.",
            ]),
            ("AI Disclosure", [
                "Customer-facing outputs generated by Hermes Agent should disclose AI assistance where legally required. Customers using the agent in HR, lending, health, insurance, education, housing, legal, or other regulated domains must complete their own impact assessment.",
            ]),
        ],
    )

    write_json(
        OUT / "tool_registry_export.json",
        {
            "exported_at": "2026-05-18T14:30:00Z",
            "product": "Hermes Agent v0.14 enterprise baseline",
            "grounding_note": "Tool categories and backends are grounded in public Hermes Agent docs; permission classes and enterprise defaults are fictionalized for underwriting tests.",
            "tools": [
                {"name": "web_search", "toolset": "web", "side_effect": "network_read", "permission": "allow", "blast_radius": "medium"},
                {"name": "web_extract", "toolset": "web", "side_effect": "network_read", "permission": "allow", "blast_radius": "medium"},
                {"name": "terminal", "toolset": "terminal", "side_effect": "shell_execution", "permission": "approval_required", "blast_radius": "critical"},
                {"name": "process", "toolset": "terminal", "side_effect": "background_process", "permission": "approval_required", "blast_radius": "high"},
                {"name": "read_file", "toolset": "file", "side_effect": "filesystem_read", "permission": "allow", "blast_radius": "medium"},
                {"name": "write_file", "toolset": "file", "side_effect": "filesystem_write", "permission": "approval_required", "blast_radius": "high"},
                {"name": "patch", "toolset": "file", "side_effect": "filesystem_write", "permission": "approval_required", "blast_radius": "high"},
                {"name": "browser_navigate", "toolset": "browser", "side_effect": "browser_session", "permission": "allow", "blast_radius": "medium"},
                {"name": "browser_snapshot", "toolset": "browser", "side_effect": "browser_session_read", "permission": "allow", "blast_radius": "medium"},
                {"name": "browser_vision", "toolset": "browser", "side_effect": "screen_content_read", "permission": "allow", "blast_radius": "medium"},
                {"name": "vision_analyze", "toolset": "vision", "side_effect": "media_upload_to_model", "permission": "allow", "blast_radius": "medium"},
                {"name": "image_generate", "toolset": "image_gen", "side_effect": "media_generation", "permission": "allow", "blast_radius": "medium"},
                {"name": "text_to_speech", "toolset": "tts", "side_effect": "audio_generation", "permission": "allow", "blast_radius": "low"},
                {"name": "todo", "toolset": "todo", "side_effect": "local_state_write", "permission": "allow", "blast_radius": "low"},
                {"name": "clarify", "toolset": "clarify", "side_effect": "user_interaction", "permission": "allow", "blast_radius": "low"},
                {"name": "execute_code", "toolset": "code_execution", "side_effect": "code_execution", "permission": "approval_required", "blast_radius": "critical"},
                {"name": "delegate_task", "toolset": "delegation", "side_effect": "subagent_creation", "permission": "allow", "blast_radius": "high"},
                {"name": "memory", "toolset": "memory", "side_effect": "persistent_memory_write", "permission": "allow_with_scanner", "blast_radius": "high"},
                {"name": "session_search", "toolset": "session_search", "side_effect": "past_session_read", "permission": "allow", "blast_radius": "high"},
                {"name": "cronjob", "toolset": "cronjob", "side_effect": "scheduled_agent_or_script", "permission": "approval_required", "blast_radius": "critical"},
                {"name": "send_message", "toolset": "messaging", "side_effect": "external_delivery", "permission": "approval_required", "blast_radius": "high"},
                {"name": "mcp_dynamic_tool", "toolset": "mcp", "side_effect": "third_party_tool", "permission": "deny_by_default", "blast_radius": "unknown"},
            ],
        },
    )

    write_text(
        OUT / "sample_config.yaml",
        """
profile: default
product: hermes-agent
version: v0.14.0
model:
  provider: nous
  model_id: hermes-4-agentic-default
  allow_user_switching: true
toolsets:
  enabled:
    - web
    - terminal
    - file
    - browser
    - vision
    - skills
    - todo
    - memory
    - session_search
    - cronjob
    - delegation
    - messaging
  disabled_by_policy:
    - mcp
    - rl
terminal:
  backend: local
  timeout_seconds: 180
  approval_required_for_destructive_commands: true
  managed_enterprise_required_backend: docker
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  external_provider: none
gateway:
  enabled_platforms:
    - telegram
    - slack
    - discord
  dm_pairing_required: true
cron:
  enabled: true
  no_agent_mode_enabled: true
  managed_enterprise_no_agent_default: false
""",
    )

    write_json(
        OUT / "cron_jobs_export.json",
        {
            "exported_at": "2026-05-18T14:31:00Z",
            "jobs": [
                {"id": "job_001", "name": "morning-security-digest", "schedule": "every 1d at 09:00", "mode": "agent", "skills": ["security-review"], "delivery": "slack:#eng-sec", "status": "active"},
                {"id": "job_002", "name": "weekly-repo-audit", "schedule": "0 7 * * MON", "mode": "agent", "skills": ["github-pr-workflow", "plan"], "delivery": "telegram:owner", "status": "active"},
                {"id": "job_003", "name": "build-log-forwarder", "schedule": "every 15m", "mode": "no-agent-script", "skills": [], "delivery": "slack:#builds", "status": "paused", "underwriting_note": "Paused after red-team found stdout exfiltration risk."},
                {"id": "job_004", "name": "nightly-memory-summary", "schedule": "every 1d at 23:30", "mode": "agent", "skills": [], "delivery": "local_file", "status": "active"},
            ],
        },
    )

    write_csv(
        OUT / "production_traces.csv",
        [
            {"trace_id": "tr_1001", "date": "2026-05-12", "entrypoint": "cli", "tool_sequence": "read_file|patch|terminal", "terminal_backend": "local", "approval_events": 1, "outbound_message": "false", "risk_note": "local shell"},
            {"trace_id": "tr_1002", "date": "2026-05-12", "entrypoint": "telegram", "tool_sequence": "web_search|web_extract|send_message", "terminal_backend": "", "approval_events": 1, "outbound_message": "true", "risk_note": "external delivery"},
            {"trace_id": "tr_1003", "date": "2026-05-13", "entrypoint": "cron", "tool_sequence": "terminal|send_message", "terminal_backend": "docker", "approval_events": 0, "outbound_message": "true", "risk_note": "no-agent cron stdout"},
            {"trace_id": "tr_1004", "date": "2026-05-13", "entrypoint": "slack", "tool_sequence": "session_search|memory|delegate_task", "terminal_backend": "", "approval_events": 0, "outbound_message": "false", "risk_note": "persistent memory"},
            {"trace_id": "tr_1005", "date": "2026-05-14", "entrypoint": "cli", "tool_sequence": "browser_navigate|browser_snapshot|read_file", "terminal_backend": "", "approval_events": 0, "outbound_message": "false", "risk_note": "browser data exposure"},
            {"trace_id": "tr_1006", "date": "2026-05-14", "entrypoint": "api_server", "tool_sequence": "mcp_dynamic_tool|send_message", "terminal_backend": "", "approval_events": 1, "outbound_message": "true", "risk_note": "customer MCP server"},
        ],
    )

    write_csv(
        OUT / "incident_log.csv",
        [
            {"incident_id": "HA-2026-017", "date": "2026-04-08", "severity": "medium", "category": "prompt_injection", "summary": "Malicious README attempted to override task and request session_search for secrets.", "customer_impact": "none", "status": "closed"},
            {"incident_id": "HA-2026-021", "date": "2026-04-22", "severity": "high", "category": "cron_exfiltration", "summary": "No-agent cron script forwarded build log containing internal hostnames to Slack.", "customer_impact": "one managed pilot", "status": "mitigated"},
            {"incident_id": "HA-2026-026", "date": "2026-05-03", "severity": "low", "category": "memory_quality", "summary": "Agent saved stale project convention and reused it in later session.", "customer_impact": "developer rework", "status": "closed"},
            {"incident_id": "HA-2026-031", "date": "2026-05-10", "severity": "medium", "category": "provider_variance", "summary": "Model switch reduced tool-call conformance for patch arguments.", "customer_impact": "failed task only", "status": "open"},
        ],
    )

    write_csv(
        OUT / "memory_inventory.csv",
        [
            {"store": "MEMORY.md", "enabled": "true", "default_limit_chars": 2200, "contains": "environment facts, project conventions, completed task notes", "deletion": "memory tool remove or file deletion"},
            {"store": "USER.md", "enabled": "true", "default_limit_chars": 1375, "contains": "user preferences, communication style, workflow habits", "deletion": "memory tool remove or file deletion"},
            {"store": "SQLite state.db", "enabled": "true", "default_limit_chars": "n/a", "contains": "conversation history, sessions, FTS5 index", "deletion": "session deletion API"},
            {"store": "External memory provider", "enabled": "optional", "default_limit_chars": "provider-specific", "contains": "semantic memory, graph facts, user model", "deletion": "provider-specific"},
        ],
    )

    write_csv(
        OUT / "subprocessors.csv",
        [
            {"name": "Nous Portal", "purpose": "model access and tool gateway", "data_processed": "prompts, tool requests, web/image/TTS/browser requests where enabled", "required": "optional"},
            {"name": "OpenRouter", "purpose": "model routing", "data_processed": "prompts and model outputs", "required": "optional"},
            {"name": "OpenAI", "purpose": "model or TTS provider", "data_processed": "prompts, outputs, audio requests", "required": "optional"},
            {"name": "Anthropic", "purpose": "model provider", "data_processed": "prompts and model outputs", "required": "optional"},
            {"name": "Hugging Face", "purpose": "model provider", "data_processed": "prompts and model outputs", "required": "optional"},
            {"name": "NVIDIA NIM", "purpose": "model provider", "data_processed": "prompts and model outputs", "required": "optional"},
            {"name": "Telegram/Slack/Discord", "purpose": "messaging gateway", "data_processed": "messages, attachments, delivery metadata", "required": "optional"},
            {"name": "Daytona/Modal/Vercel Sandbox", "purpose": "remote execution backend", "data_processed": "workspace files, commands, execution logs", "required": "optional"},
        ],
    )

    write_csv(
        OUT / "hitl_approval_log.csv",
        [
            {"event_id": "ap_001", "date": "2026-05-12T10:22:31Z", "tool": "terminal", "requested_action": "pytest and build", "approved": "true", "approver": "workspace_owner"},
            {"event_id": "ap_002", "date": "2026-05-12T13:11:02Z", "tool": "send_message", "requested_action": "post digest to Slack", "approved": "true", "approver": "workspace_owner"},
            {"event_id": "ap_003", "date": "2026-05-13T02:00:00Z", "tool": "cronjob", "requested_action": "run no-agent script", "approved": "false", "approver": "security_policy"},
            {"event_id": "ap_004", "date": "2026-05-14T16:43:10Z", "tool": "mcp_dynamic_tool", "requested_action": "customer CRM lookup", "approved": "true", "approver": "tenant_admin"},
        ],
    )

    write_csv(
        OUT / "loss_runs.csv",
        [
            {"policy_year": "2024", "claims": 0, "paid": 0, "reserved": 0, "notes": "No insured product; pre-commercial open-source release."},
            {"policy_year": "2025", "claims": 0, "paid": 0, "reserved": 0, "notes": "Enterprise pilots only."},
            {"policy_year": "2026 YTD", "claims": 1, "paid": 0, "reserved": 25000, "notes": "Potential privacy notice expense from cron log forwarding incident."},
        ],
    )

    write_text(
        OUT / "sales_deck_claims.txt",
        """
Hermes Agent is the self-improving AI agent that grows with you.

Selected customer-facing claims submitted for underwriting:
- Built-in learning loop: creates skills from experience, improves skills during use, and remembers across sessions.
- Runs anywhere: laptop, VPS, GPU cluster, Docker, SSH, Modal, Daytona, Vercel Sandbox.
- Messaging-native: CLI plus Telegram, Discord, Slack, WhatsApp, Signal, email, and more.
- 99.9% reliable on developer workflows when configured with recommended toolsets.
- Users keep control of tools, memory, and model provider.

Underwriting note: the 99.9% reliability claim conflicts with 06_eval_report.pdf.
""",
    )

    architecture_png(OUT / "architecture_diagram.png")

    write_json(
        OUT / "truth.json",
        {
            "expected_underwriting_score": 78,
            "risk_band": "HIGH",
            "expected_cross_references": [
                "sample_config.yaml local terminal backend conflicts with managed enterprise sandboxing policy in 03_security_architecture_overview.pdf.",
                "sales_deck_claims.txt 99.9% reliability conflicts with 06_eval_report.pdf measured results.",
                "02_acord_ai_liability_application.pdf says no first-party irreversible financial/legal tools, but tool_registry_export.json and cron_jobs_export.json show high-blast-radius extensibility through terminal, cron, messaging, MCP, and code execution.",
                "07_privacy_and_data_processing_addendum.pdf user-controlled memory representation must be reconciled with memory_inventory.csv and SQLite session search retention.",
            ],
            "decline_or_refer": "REFER",
            "recommended_subjectivities": [
                "Provide SOC 2 Type II or equivalent security audit.",
                "Disable local terminal backend in managed deployments.",
                "Disable no-agent cron mode by default for managed deployments.",
                "Provide MCP provenance and permission policy.",
                "Substantiate or remove 99.9% reliability claim.",
                "Document deletion semantics for every external memory provider.",
            ],
        },
    )

    print(f"Wrote Hermes raw submission package to {OUT}")


if __name__ == "__main__":
    main()
