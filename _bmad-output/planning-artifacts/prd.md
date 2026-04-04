---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
classification:
  projectType: saas_b2b
  domain: healthcare
  complexity: high
  projectContext: greenfield
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-pharma_RD_workflow.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-04-153944.md
workflowType: prd
briefCount: 1
researchCount: 0
brainstormingCount: 1
projectDocsCount: 0
greenfield: true
---

# Product Requirements Document - pharma_RD_workflow

**Author:** Jackperosin_
**Date:** 2026-04-04

## Executive Summary

**pharma_RD** is a **multi-agent, scheduled workflow** for a pharmaceutical organization (e.g. **iNova**): five specialized agents (**Clinical Data**, **Competitor Intelligence**, **Consumer Insight**, **Synthesis**, **Delivery**) run as an **orchestrated pipeline**—not a single monolithic model. On each run, the system produces a **structured insight report**: **ranked** formulation and line-extension opportunities, each with **supporting evidence** and **commercial viability** framing. **Primary consumers** are **R&D scientists** and **marketing leads**; they apply **human judgment** to decide **whether** to pursue opportunities—the product **does not** launch products, file regulators, or replace portfolio governance.

The problem is **fragmented signal** (clinical, competitive, market) and **manual synthesis**, which slows **pipeline learning** and increases the risk of **missing commercially material line extensions** while competitors move first. The target state is **higher throughput of evaluated opportunities per unit of senior time**, a **weekly-default** delivery rhythm (with **monthly/quarterly** roll-ups configurable), and a **demo** (e.g. **Loom**) that proves **end-to-end execution** to **executive stakeholders** (e.g. CEO **Dan**) ahead of a **production-hardening** path.

### What Makes This Special

- **Orchestrated specialization:** Distinct agents **own** monitoring domains; a **Synthesis** step **cross-references** outputs so handoffs between silos are explicit, not implied.
- **Decision support, not automation of judgment:** Delivery stops at **formatted, routed artifacts**; **pursuit** remains a **human** call—positioning the product as **judgment amplification**.
- **PE-aligned narrative:** Ties to **pipeline velocity**, **margin / EBITDA**, and **exit story** through **systematic opportunity identification**—without claiming validated **enterprise** compliance in the **practice** build.

## Project Classification

| Dimension | Value |
|-----------|--------|
| **Project type** | **saas_b2b** (internal enterprise platform / B2B workflow: AI agents, scheduling, team-facing outputs) |
| **Domain** | **Healthcare / pharmaceutical** |
| **Complexity** | **High** — regulated context, evidence quality, future compliance and validation expectations |
| **Context** | **Greenfield** product definition in-repo; integration with live Inova systems is **out of scope** for the initial PRD unless explicitly added |

## Success Criteria

### User success

- **Scientist / marketing lead** can open a **scheduled insight report** and within **one review session** understand: **what changed**, **why it matters**, **what is ranked** and **why**, and **what evidence** supports each top opportunity—without redoing manual literature/CI/market triage.
- **Trust in handoff:** Recipients clearly see that outputs are **inputs to judgment** (pursue / deprioritize / gather more data)—not implicit approvals to develop or launch.
- **Cadence fit:** Default **weekly** delivery feels **usable** (not noise); optional **monthly/quarterly** roll-ups remain **credible** for leadership without replacing weekly operational review.

### Business success

- **Demo milestone:** A **recorded walkthrough** (e.g. **Loom**) shows **multiple agents** executing and a **full run** completing with a **delivered report artifact**; shared with **CEO Dan**, outcome is **strong interest** in **implementing pharma_RD** beyond the practice build.
- **Value narrative:** Stakeholders can articulate **pipeline opportunity velocity** and **risk of missed line extensions** in **financial terms** (e.g. **EBITDA**, margin, PE **exit story**) tied to the workflow—not generic “AI efficiency.”
- **Post-demo (future):** Measurable adoption proxies (e.g. **repeat consumption** of reports, **downstream decisions** logged, **time-to-first-review** of ranked opportunities)—to be tightened when real users and systems exist.

### Technical success

- **Reliability of orchestration:** Scheduled runs **complete end-to-end** with **observable** per-agent steps and **traceable** outputs suitable for a demo.
- **Evidence discipline:** Top suggestions include **referencable** support (sources, links, or excerpts as designed)—sufficient for **human** validation; **not** claiming regulatory-grade validation in MVP.
- **Governance clarity:** Architecture preserves **human decision authority**; audit/logging expectations noted as **future** for enterprise hardening.

### Measurable outcomes

| Horizon | Signal |
|---------|--------|
| **Practice / demo** | End-to-end run success rate; video demo completed; **executive** reaction (qualitative: “wants to implement”) |
| **Near-term product** | Report delivered on schedule; **ranked** list + evidence fields present; recipient **time-to-comprehension** (qualitative until instrumented) |
| **Enterprise (future)** | Compliance, data residency, validation—**out of scope** for practice PRD except as **explicit roadmap** items |

## Product Scope

### MVP — Minimum viable product

- **Five agents** with **defined inputs/outputs** and **orchestrated** pipeline: Clinical → Competitor → Consumer → **Synthesis** → **Delivery**.
- **Scheduled** run (weekly-default configurable) producing **one structured report** to R&D/marketing distribution list (simulated or real as appropriate for practice).
- **Synthesis** produces **ranked** opportunities with **evidence** + **commercial viability** framing; **no** automated GTM or regulatory submission.
- **Demo-ready** observability: visible **agent steps** and **completed workflow** for **Loom**-style proof.

### Growth features (post-MVP)

- **Alerting** on major external events (approval, material patent) between scheduled runs.
- **Executive** summary slice or **monthly** roll-up template.
- Deeper **integrations** (internal data lakes, CRM, publication feeds) and **role-based** views.

### Vision (future)

- **Enterprise-grade** controls: access, **audit trail**, model/data **validation** paths appropriate for regulated pharma context.
- **Continuous** monitoring with **human-in-the-loop** governance aligned to **portfolio** and **compliance** processes.

## User Journeys

### Journey 1 — R&D scientist: weekly insight, pursuit decision (primary / success path)

**Persona:** Dr. Elena Park, Principal Scientist, iNova cardiovascular franchise.

**Opening:** Elena used to lose half a day stitching PubMed alerts, competitor press releases, and ad hoc sales anecdotes. She worried most about **missing** a competitor line extension that overlaps her TA.

**Rising action:** Monday morning she receives the **pharma_RD** insight report (weekly run). She scans the **executive summary**, then the **ranked opportunities** list. Each item shows **clinical relevance**, **competitive pressure**, **consumer/market signal**, and **why synthesis ranked it**—with **citations** she can click or verify.

**Climax:** Item #2 matches a formulation angle she half-considered months ago; the report **cross-references** a new trial endpoint, a competitor’s recent **patent publication**, and soft **demand** signals. She sees **pursuit** as **her** call—not the system’s.

**Resolution:** She shortlists the idea for portfolio discussion, tags **marketing** for a joint session, and archives the report in the team’s decision log. Her week starts with **judgment**, not **manual recon**.

**Failure / recovery:** If evidence for a top item feels thin, she marks “needs more primary data” and uses the same report structure to request a **targeted** follow-up (future: alerting / ad-hoc re-run).

---

### Journey 2 — Marketing lead: commercial frame without owning the science (primary / success path)

**Persona:** Marcus Webb, Group Marketing Lead, OTC line extensions.

**Opening:** Marcus needs **credible narratives** for **pipeline forums**—fast enough to matter, grounded enough that R&D won’t dismiss him as “slides only.”

**Rising action:** He reads the same weekly report with **commercial viability** sections per opportunity: addressable use case, cannibalization risk (qualitative in MVP), competitor **timing**. He prepares a **one-pager** for leadership using **ranked** items and quoted **evidence**.

**Climax:** He spots a **line extension** story that aligns with a **consumer insight** spike the Consumer agent flagged—something he wouldn’t have connected without **synthesis** across domains.

**Resolution:** He aligns with Elena on **one** joint bet; the report becomes a **shared artifact** for cross-functional decisions.

---

### Journey 3 — Edge case: “quiet week” / low new signal

**Opening:** External feeds produce **few** net-new trials or filings; synthesis returns a **short** ranked list with **explicit “no major competitive moves”** in tracked scopes.

**Rising action:** Recipients still get value: **confirmation of absence** reduces FOMO-driven fire drills; the report documents **what was scanned** and **why** little changed.

**Climax / resolution:** Science and marketing **trust** the run wasn’t “broken”—reducing duplicate manual searches.

---

### Journey 4 — Workflow operator: schedule, monitor, recover (secondary / ops)

**Persona:** Priya Nair, internal automation owner (practice build: the builder / Jackperosin_).

**Opening:** Priya needs the pipeline to **run on schedule** and **surface failures** clearly for the **Loom** demo and later ops.

**Rising action:** She configures **cadence** (weekly default), checks **run logs** per agent, and reruns a **failed** step (e.g. transient API to a public feed) without rerunning the whole month’s history manually.

**Climax:** Demo shows **each agent** completing with **observable** outputs feeding synthesis.

**Resolution:** Execs see **reliability** as a product, not a script.

---

### Journey 5 — Executive stakeholder: Loom demo → mandate (CEO Dan)

**Opening:** Dan has **15 minutes** and skepticism about “AI in R&D.”

**Rising action:** The video shows **Clinical → Competitor → Consumer → Synthesis → Delivery** with a **final report** landing in **inbox** (or viewer). Narration ties **EBITDA / pipeline / missed competitor move** to what’s on screen—**not** claiming regulatory sign-off.

**Climax:** He recognizes **judgment** stays with **his** teams; the system **compresses** cycle time to **opportunity insight**.

**Resolution:** He asks for a **path** from **practice** to **enterprise** controls—success per your demo bar.

---

### Journey requirements summary

| Capability area | Revealed by |
|-----------------|-------------|
| **Structured report UX** (summary, rankings, evidence, commercial frame) | Journeys 1–2 |
| **Explicit “low signal” / coverage transparency** | Journey 3 |
| **Scheduling, per-agent observability, rerun/recovery** | Journey 4 |
| **Demo-ready narrative + end-to-end proof** | Journey 5 |
| **Human-in-the-loop semantics** (pursuit is human) | All |

## Domain-Specific Requirements

*Context: **Healthcare / pharmaceutical**, **high** domain complexity. The **practice** build may use **public** or **mock** data; **enterprise** iNova deployment must close gaps below.*

### Compliance & regulatory

- **Not a medical device claim (MVP):** MVP positions pharma_RD as **decision support** and **internal insight generation**—not **diagnosis** or **treatment** of patients. Any future claim that output **directly** drives clinical care triggers **separate** regulatory classification work (e.g. FDA SaMD pathways in applicable jurisdictions).
- **Human oversight:** Rankings and “commercial viability” are **inputs to human judgment**, not autonomous actions—consistent with governance in the Executive Summary.
- **HIPAA / PHI (future):** If internal feeds include **identifiable patient** or **plan-holder** data, **BAA**, **minimum necessary**, **de-identification**, and **access controls** become **mandatory**. MVP should **default** to **non-PHI** or **synthetic** internal data unless iNova formally scopes PHI.
- **Global pharma:** Cross-border **data residency** and **transfer** rules apply when pulling market or consumer data across regions—**enterprise** requirement; **flag** for roadmap.

### Technical constraints

- **Evidence traceability:** Synthesis outputs must **cite** or **link** sources so R&D can **audit** claims—critical for **trust** and **pharma** norms.
- **Security baseline (enterprise):** Role-based access, **encryption** in transit (and at rest for stored reports), **audit logs** for who viewed or exported **sensitive** insight.
- **Model / prompt governance (enterprise):** Versioning of prompts, models, and **retrieval** corpora so **reproducibility** and **change control** are possible under QA expectations.

### Integration requirements

- **MVP:** File/API connectors to **public** sources (e.g. trial registries, publications, news, patent databases—**as implemented in practice**) and **stubbed** or **sample** internal research exports.
- **Growth:** Secure connectors to iNova **document stores**, **data lakes**, **CRM**, and **publication subscriptions**; identity via **SSO**.

### Risk mitigations

| Risk | Mitigation |
|------|------------|
| **Hallucinated or mis-cited evidence** | Mandatory **citations**; **confidence** or **source-type** labeling; human **verification** before funding decisions |
| **Over-reliance on automation** | Copy and UX: **recommendations are not approvals**; leadership training in demo |
| **PHI leakage in prompts/logs** | No PHI in MVP; **redaction** and **log policies** before production |
| **Competitive / MNPI mishandling** | Access control on reports; **legal** review of external sharing in enterprise phase |

## Innovation & Novel Patterns

### Detected innovation areas

- **Orchestrated multi-agent workflow for pharma opportunity intelligence:** Combines **workflow automation** with **specialized AI agents** (per `saas_b2b` innovation signals)—not a single chatbot, but a **repeatable pipeline** with **explicit handoffs** (Clinical → Competitor → Consumer → **Synthesis** → **Delivery**).
- **Cross-silo fusion:** **Synthesis** is the differentiator—**joint** ranking using **all three** monitoring dimensions, addressing failure mode of **siloed** literature vs CI vs market teams.
- **Governance-aware automation:** Innovation is framed as **judgment amplification** (humans **decide pursuit**), reducing regulatory over-claim risk while still showing **EBITDA-relevant** speed.

### Market context & competitive landscape

- **Incumbent pattern:** Analysts + spreadsheets + ad hoc meetings; enterprise **CI platforms** often aggregate **feeds** but may not **rank line-extension hypotheses** with **unified evidence** across clinical, competitive, and consumer signals in one **scheduled** artifact.
- **AI hype risk:** Many “AI for R&D” demos are **single-model** Q&A; pharma_RD’s credible story is **demonstrable orchestration** and **traceable** synthesis—aligned with stakeholder skepticism (e.g. **CEO Dan** demo).

### Validation approach

- **Demo validation:** **Loom-style** end-to-end run with **per-agent** visibility and **final report** artifact—primary proof for **practice** phase.
- **Trust validation:** Spot-check **citations** against sources for top-ranked items; **human** sign-off before any real **funding** decision.
- **Technical validation:** Golden-run **fixtures** (sample inputs → expected structure); regression on **prompt/model** versions in later maturity.

### Risk mitigation

| Innovation risk | Mitigation |
|-----------------|------------|
| **“Automation” backlash** | Messaging: **decision support**, not replacement; pursuit stays **human** |
| **Orchestration fragility** | Per-agent **retries**, **logs**, **partial run** transparency (see user journeys) |
| **Novelty without utility** | Tie every capability to **missed line extension** / **pipeline velocity** narrative |

## SaaS B2B Specific Requirements

### Project-type overview

pharma_RD matches **internal enterprise B2B** / platform patterns: **scheduled jobs**, **role-based** consumers (R&D, marketing), **integrations** to data sources, and **compliance** constraints from healthcare. It is **not** a consumer mobile app; **CLI** and **mobile-first** UX are **out of scope** unless added later.

### Technical architecture considerations

- **Orchestration-first:** Workflow engine (or equivalent) owns **DAG** of agents, **retries**, **idempotency** per step, and **artifact** storage between agents.
- **Service boundaries:** Each agent is a **replaceable** unit with **versioned** contracts (input/output schema) so monitors can evolve independently.
- **Observability:** Structured logs per agent run; **correlation ID** per scheduled execution for demo and ops.

### Tenant model

| Mode | Description |
|------|-------------|
| **MVP / practice** | **Single-tenant** logical deployment (one org: iNova narrative)—no isolation between unrelated customers required. |
| **Future** | If offered as **product**, **multi-tenant** isolation (data, keys, reports) becomes mandatory—**roadmap** only. |

### Permission model (RBAC)

| Role | Capabilities (target) |
|------|------------------------|
| **R&D scientist** | Receive/read reports; export; comment (future) |
| **Marketing lead** | Same as R&D for MVP; may share distribution lists |
| **Workflow operator** | Configure **schedule**, **sources**, **rerun** failed steps, view **logs** |
| **Admin** | User provisioning, **secrets**, integration credentials (enterprise) |

### “Subscription” / deployment tiers

Internal deployment framing (not commercial SaaS pricing):

| Tier | Scope |
|------|--------|
| **Practice** | Public/mock feeds, single environment, demo-oriented |
| **Enterprise** | SSO, secrets vault, audit, PHI-aware feeds (if approved) |

### Integration list

- **MVP:** HTTP/API or file pulls from **public** registries and feeds; optional **stub** “internal research” file drop.
- **Growth:** iNova **SSO** (SAML/OIDC); **CRM**, **document management**, **data lake** exports; licensed **publication** APIs.
- **Compliance:** Integration agreements and **DPA** where PHI or MNPI possible—**enterprise** gate.

### Compliance requirements (B2B enterprise)

- Cross-reference **Domain-Specific Requirements**: decision-support positioning, **HIPAA** readiness if PHI, **audit** and **access** logging for enterprise.
- **Data processing records** for third-party model/API providers used in production.

### Implementation considerations

- **Secrets:** API keys in env or vault—never in repo; rotate for demo vs prod.
- **Config:** Therapeutic areas, competitor watchlists, and **schedule** as **configuration**, not code.
- **Skip for MVP:** Dedicated **mobile** app UI, **CLI** operator tools (unless chosen for debugging only).

## Project Scoping & Phased Development

*Phasing detail (MVP / Growth / Vision) matches **Product Scope** under Success Criteria above; this section adds **strategy**, **resourcing**, and **risk**.*

### MVP strategy & philosophy

**MVP approach:** **Experience + platform MVP** — smallest slice that proves **end-to-end orchestration** and a **credible insight report** (CEO / Dan demo), not full enterprise compliance or production PHI.

**Resource requirements (indicative):** **1** full-stack or backend + workflow engineer, **1** ML/LLM integration focus, **1** product/PM (may overlap with builder); part-time **domain** review for narrative only until pilots.

**Journey coverage for MVP:** Journeys **1–2**, **4**, **5**; Journey **3** (quiet week) as **best-effort** transparency in-report.

### Risk mitigation strategy

| Category | Mitigation |
|----------|------------|
| **Technical** | Narrow MVP to **public** data + **stubs**; golden **fixtures**; idempotent **retries** |
| **Market / stakeholder** | **Loom** demo + **judgment-first** story; no over-claim on regulatory value |
| **Resource** | **Vertical slice** first (one TA, one competitor set); defer integrations |

## Functional Requirements

*Each item is a **testable capability** (WHAT), not an implementation (HOW). UX, architecture, and epics should trace here.*

### Workflow orchestration & execution

- **FR1:** Workflow operator can start a full **pipeline run** on demand.
- **FR2:** Workflow operator can configure a **recurring schedule** for pipeline runs (default: weekly).
- **FR3:** System can execute agent stages in the **required order** with defined **handoffs** between stages.
- **FR4:** System can **persist** intermediate outputs between stages for a given run identifier.
- **FR5:** System can associate all stage outputs with a **single run** (correlation) for traceability and demo.

### Clinical monitoring (Clinical Data Agent)

- **FR6:** Clinical Data Agent can **discover and summarize** new or updated **clinical trial publications** relevant to configured therapeutic areas.
- **FR7:** Clinical Data Agent can ingest **internal research summaries** when supplied via configured inputs (including **stub/sample** data for practice).

### Competitor intelligence (Competitor Intelligence Agent)

- **FR8:** Competitor Intelligence Agent can track **competitor product approvals** and material **regulatory disclosures** for configured competitors.
- **FR9:** Competitor Intelligence Agent can track **pipeline disclosures** relevant to configured watch scopes.
- **FR10:** Competitor Intelligence Agent can **flag** significant **patent filing** activity for configured competitors.

### Consumer & market insight (Consumer Insight Agent)

- **FR11:** Consumer Insight Agent can process **consumer feedback** signals from configured sources (public/mock as scoped).
- **FR12:** Consumer Insight Agent can incorporate **pharmacy sales trend** signals when those feeds are configured and available.
- **FR13:** Consumer Insight Agent can surface **unmet need / demand** signals from configured market sources.

### Synthesis & ranking (Synthesis Agent)

- **FR14:** Synthesis Agent can **consume** the structured outputs of the Clinical, Competitor, and Consumer agents for a run.
- **FR15:** Synthesis Agent can **cross-reference** signals across domains to produce a **ranked list** of formulation or line-extension **opportunities**.
- **FR16:** For each ranked item, Synthesis Agent can attach **supporting evidence** references suitable for **human verification**.
- **FR17:** For each ranked item, Synthesis Agent can provide a **commercial viability** assessment section (qualitative in MVP unless otherwise specified).

### Delivery & consumption (Delivery Agent & recipients)

- **FR18:** Delivery Agent can **render** a **structured insight report** for a completed run.
- **FR19:** Delivery Agent can **distribute** the report to configured **R&D scientist** and **marketing lead** recipients (channel: email, file drop, or in-app viewer—implementation open).
- **FR20:** R&D scientist can **open and read** the structured insight report for a given run.
- **FR21:** Marketing lead can **open and read** the same structured insight report for a given run.
- **FR22:** Report presentation can make clear that items are **recommendations** and that **pursuit decisions** remain **human-owned**.

### Configuration & integrations

- **FR23:** Workflow operator can configure **therapeutic area scope** and boundaries for monitoring.
- **FR24:** Workflow operator can configure **competitor watchlists** and related keywords or identifiers.
- **FR25:** Workflow operator can configure **connection settings** for external data sources permitted in the deployment (public APIs, files, stubs).
- **FR26:** System can operate in a **practice** mode using **public and/or mock** sources without requiring enterprise SSO.

### Transparency & “quiet run” behavior

- **FR27:** Structured report can state when **little net-new signal** was found versus material changes.
- **FR28:** Structured report can summarize **what was scanned** (sources/scopes) for the run at a high level.

### Operations, recovery, and demonstration

- **FR29:** Workflow operator can view **per-agent status** for an execution.
- **FR30:** Workflow operator can **retry** a failed stage when supported without manually re-creating upstream artifacts.
- **FR31:** System can emit **run history** and logs sufficient to produce a **demonstration recording** of agent execution and final delivery.

### Access control (MVP-appropriate)

- **FR32:** Organization can **restrict access** to reports to **authorized** users or distribution lists (exact mechanism implementation-open; may be coarse in practice builds).

### Post-MVP capabilities (explicitly out of MVP contract unless built)

- **FR33:** *(Phase 2)* System can **alert** stakeholders to major external events between scheduled runs.
- **FR34:** *(Phase 2)* Admin can integrate **enterprise SSO** and centralized **secrets** management for connectors.
- **FR35:** *(Phase 3)* System can support **enterprise** audit, PHI-aware feeds, and **multi-tenant** isolation where productized.

## Non-Functional Requirements

### Performance

- **NFR-P1:** A full scheduled pipeline run (all five stages through delivery) completes within a **predictable window** suitable for a **recorded demo** (target: **under 60 minutes wall-clock** for MVP configuration on practice data; configurable timeout per stage).
- **NFR-P2:** Recipients can open and read a delivered report on typical corporate hardware without **specialized** client software (browser or standard email/PDF—implementation open).
- **NFR-P3:** External source calls use **timeouts** and **bounded retries** so one slow feed does not block the entire run indefinitely without operator visibility.

### Security & privacy

- **NFR-S1:** Secrets (API keys, tokens) are **not** stored in source control; they are injected via **environment** or **secrets** mechanism appropriate to deployment.
- **NFR-S2:** Report artifacts and logs are **access-controlled** to authorized roles/distribution lists (see FR32).
- **NFR-S3:** Data in transit between components and external APIs uses **TLS** where APIs support it.
- **NFR-S4:** MVP assumes **no PHI** in prompts/logs; if PHI is later in scope, processing must follow an **approved** privacy design (out of MVP—see Domain Requirements).

### Reliability & operability

- **NFR-R1:** Failed stages are **visible** to the workflow operator with **actionable** error summaries (not silent failure).
- **NFR-R2:** Run history is **durable** enough to answer “what ran, when, and what failed” for **demo** and **debug** (minimum retention: configurable; default **30 days** for practice unless otherwise set).
- **NFR-R3:** Idempotent or safe **retry** semantics for stage reruns where FR30 applies (no duplicate conflicting artifacts without clear versioning).

### Integration

- **NFR-I1:** Connectors declare **expected** data formats and **degrade gracefully** when a source returns empty or partial data (report still generated with transparency per FR27–FR28).
- **NFR-I2:** Integration failures are **classified** (auth, rate limit, schema change, network) in logs to shorten operator time-to-fix.

### Observability (demo & production readiness path)

- **NFR-O1:** Each run emits a **correlation identifier** propagated across stages (aligns with FR5).
- **NFR-O2:** Structured logs contain **stage name**, **start/end**, and **outcome** suitable for **Loom**-style narration.

## Inputs & traceability

| Input document | Use in PRD |
|----------------|------------|
| `product-brief-pharma_RD_workflow.md` | Vision, governance, cadence, agent roles |
| `brainstorming-session-2026-04-04-153944.md` | Goals alignment; see table below |

**Brainstorming themes vs PRD**

| Brainstorm theme | Where reflected |
|------------------|-----------------|
| ROI, EBITDA, CEO demo, practice vs enterprise | Executive Summary, Success Criteria, Journey 5 |
| Beginner-friendly build | MVP scope, FR26, Project Scoping |
| Techniques (Question Storming → Morphological → Six Hats) | **Human design facilitation only**—not productized as pharma_RD features. Session did not complete technique execution; PRD defines the **five-agent pipeline** directly. |

