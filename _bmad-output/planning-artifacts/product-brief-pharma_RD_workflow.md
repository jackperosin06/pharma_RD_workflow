---
title: "Product Brief: pharma_RD"
project_name: pharma_RD_workflow
product_code_name: pharma_RD
status: complete
updated: "2026-04-04"
version: "1.1"
audience: "Executive (CEO), R&D leadership, Marketing leadership"
communication_language: English
---

# pharma_RD — Product Brief

**Executive summary:** **pharma_RD** is a **multi-agent, orchestrated workflow** (not a single monolithic agent) designed for a global pharmaceutical company such as **iNova**. It runs on a **schedule**, continuously monitors **clinical**, **competitive**, and **market** signals, and delivers a **structured insight report** that ranks **formulation and line-extension opportunities** with **evidence** and **commercial viability**—so R&D and marketing move faster than competitors and miss fewer high-value moves. **Humans remain the decision authority:** the system **does not** launch products or replace portfolio governance; it **elevates** expert judgment by removing manual signal-gathering.

---

## Problem & opportunity

R&D and marketing teams must synthesize **fragmented** information: new trials and internal research, competitor **approvals, pipeline, and IP**, and **consumer and trade signals**. Manual synthesis is slow, inconsistent, and prone to **missing commercially significant line extensions** while competitors act first. For a **PE-owned** business, **pipeline velocity**, **margin expansion**, and a credible **growth / exit narrative** depend on converting signal into **prioritized opportunity** faster than the status quo.

---

## Product concept

| Attribute | Description |
|-----------|-------------|
| **Name** | **pharma_RD** |
| **Type** | Scheduled **multi-agent pipeline** with explicit handoffs and a single end-to-end **workflow** |
| **Primary users** | R&D scientists, marketing leads (consumers of **insight artifacts**); operators may tune schedules and sources in a full deployment |
| **Output** | Recurring **structured insight reports** (ranked opportunities, evidence, commercial viability notes)—**decision support**, not product launch |

**pharma_RD is explicitly multi-agent:** each agent owns **one** specialized job; an orchestration layer runs them as a **pipeline** and composes outputs.

---

## Governance, human judgment, and handoff

**What pharma_RD does *not* do**

- It does **not** take products to market, file regulatory submissions, or execute commercial campaigns.
- It does **not** replace **portfolio**, **medical**, or **compliance** governance; it produces **research and insight artifacts** for people who already own those accountabilities.

**What the Delivery Agent does**

- The **Delivery Agent** only **formats** and **routes** the final **structured insight report** to **R&D scientists** and **marketing leads** on the agreed **cadence** (see below). Its job ends at **trusted, repeatable delivery** of **decision-ready material**.

**Human-in-the-loop (non-negotiable)**

- **Scientists and marketing leads** apply **years of domain judgment** to decide **whether** a suggested opportunity is **worth pursuing**—funding lab work, validation, business cases, or **stopping** before sunk cost.
- The shift is **role elevation**, not role elimination: teams move from **high hours in manual monitoring** (searching literature, tracking competitors, stitching spreadsheets) to **higher-leverage work**—evaluating **pre-synthesized**, **evidence-linked** options at **greater throughput**. That increases how much R&D and marketing can **evaluate per unit of time**, which supports **faster portfolio learning** and, for iNova, **stronger growth** from the **same** senior talent.

**Dynamic of the change**

| Before | After (with pharma_RD) |
|--------|-------------------------|
| Manual “weeds of the internet” triage and stitching | **Judgment-first** review of AI-prepared, **ranked** opportunities with **citations and rationale** |
| Limited bandwidth → fewer hypotheses tested | **More** hypotheses and evidence packages reviewed per cycle |
| Inconsistent capture of competitive moves | **Systematic** monitoring + **single** synthesis step |

---

## Delivery cadence (industry-informed)

Pharmaceutical **competitive intelligence** and **R&D strategy** practice does not reduce to a single global “right” frequency. Industry material describes **layered horizons**—e.g. **strategic** (multi-year modalities and platforms), **tactical** (pipeline and regulatory moves over roughly **1–3 years**), and **operational** (conferences, approvals, filings, alerts)—with modern CI emphasizing **continuous** monitoring and **analysis over raw aggregation**, not only **quarterly** snapshots.

**Recommendation for pharma_RD (configurable per iNova)**

| Layer | Typical use | Role for pharma_RD |
|-------|-------------|---------------------|
| **Weekly (default for the core report)** | Operational rhythm: new trials, filings, and market signals accumulate quickly; a **weekly structured insight report** matches how many teams run **tactical** CI and avoids **stale** prioritization between cycles. | **Primary** scheduled run: full pipeline → **Synthesis** → **Delivery** to R&D and marketing. |
| **Monthly** | Deeper **portfolio** or **therapeutic-area** review; often aligns with internal **commercial / R&D** cadences. | Optional **add-on** digest or **executive summary** slice (same system, different template/audience). |
| **Quarterly** | Board- and **strategy**-adjacent reviews; **annual** pipeline reports remain common at **industry** level for macro trends. | Optional **roll-up** of weekly/monthly outputs for **leadership**—not a replacement for continuous monitoring. |

**Why not “quarterly only”?** For **line extensions** and **competitor first-mover** risk, **three-month** gaps can be too slow for **actionable** early warning; **weekly** (with **alerting** for major events in a full build) aligns with **operational CI** norms. **Quarterly** remains right for **strategic** narrative, not necessarily for **first-pass** scientist/marketing review.

**Product implication:** The **schedule** must be a **first-class setting** (weekly default; monthly/quarterly variants and **ad-hoc** re-runs for major events in a mature deployment).

---

## Agent roles (pipeline)

1. **Clinical Data Agent** — Monitors and summarizes **new clinical trial publications** and **internal research data** relevant to iNova’s **therapeutic areas**.
2. **Competitor Intelligence Agent** — Tracks **competitor approvals**, **pipeline disclosures**, and **patent filings**; **flags** material changes.
3. **Consumer Insight Agent** — Processes **consumer feedback**, **pharmacy sales trends**, and **unmet-need** signals from the market.
4. **Synthesis Agent** — Ingests outputs from the three monitoring agents, **cross-references** them, and produces **ranked suggestions** for **new formulations or line extensions**, each with **supporting evidence** and a **commercial viability assessment**—**inputs to human judgment**, not automatic commitments.
5. **Delivery Agent** — Formats the final **insight artifact** and **distributes** it to **R&D scientists** and **marketing leads** on the **defined schedule**—**only** delivery and formatting; **no** go-to-market execution.

---

## Value proposition

- **Speed:** Faster identification of **pipeline opportunities** from integrated signals.
- **Risk reduction:** Lower chance of **missing a commercially significant line extension** while a competitor ships first.
- **Human leverage:** Senior R&D and marketing spend **less time gathering** and **more time deciding**—raising **throughput** of evaluated opportunities and supporting **company growth** without duplicating headcount.
- **Financial narrative (PE context):** Supports **pipeline velocity**, **margin expansion**, and **exit-story value** by making opportunity identification more systematic and repeatable.

---

## Success criteria — demo (explicit)

**Success** for the initial demonstration is **not** full enterprise certification—it is **stakeholder conviction** through **visible execution**:

- A **Loom-style video** that shows **multiple specialized agents** executing their steps and **completing the end-to-end workflow** (monitor → synthesize → **delivery of insight artifacts** to human roles).
- Sharing that demo with **CEO Dan** such that he is **strongly impressed** and **wants to implement pharma_RD** for real.

Secondary signals: clarity of the **report structure**, plausibility of **evidence linkage**, explicit **governance** story (humans decide pursuit), and a credible path from **demo** to **production-grade** controls (data access, validation, compliance)—acknowledged as **out of scope** for the practice build but **on the roadmap** for a true enterprise rollout.

---

## Scope notes (from discovery)

- **In scope for narrative:** iNova-class pharma, PE-style value story, multi-agent orchestration, scheduled delivery, ranked opportunities with evidence and commercial lens, **human judgment** as the **final gate**, **weekly-default** cadence with **monthly/quarterly** roll-ups as options.
- **Explicitly out of scope for “practice” build:** Full **enterprise integration** (validated GxP, production data contracts, formal medical/regulatory sign-off). The brief still describes the **target** product so a future PRD can harden requirements.

---

## Strategic fit (iNova)

pharma_RD positions iNova to treat **innovation intelligence** as a **repeatable operating system**: same inputs every cycle, comparable **ranking** and **rationale**, and a rhythm—**weekly by default**—that matches **tactical** industry practice while allowing **monthly** and **quarterly** layers for **portfolio and board** storytelling. The CEO demo validates **strategic** and **financial** pull; **scientists and marketing leads** see a credible story: **less manual digging**, **more** **judgment applied** to **better-prepared** work.

---

*Prepared for: Jackperosin_ — English language outputs per BMad configuration.*
