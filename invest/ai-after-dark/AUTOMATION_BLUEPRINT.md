# AI AFTER DARK — Capital Engine Automation Blueprint

**Goal:** one founder action starts investor/partner discovery, evidence collection, scoring, compliant outreach, reply monitoring, qualification and notification.

**Design constraint:** automation must never silently cross from business-development outreach into an unapproved securities solicitation.

---

## 1. One-button behavior

```bash
capital-engine run
```

Expected behavior:

1. load campaign configuration and compliance mode;
2. verify required legal/identity settings;
3. search allowed public sources and configured APIs;
4. create evidence-backed prospect records;
5. deduplicate against the local CRM;
6. enrich investor/partner thesis, stage, geography, check size and portfolio adjacency;
7. calculate a deterministic fit score;
8. generate a short personalized message using only verified prospect facts;
9. run message through compliance and suppression checks;
10. send or draft according to policy;
11. poll the campaign inbox for replies;
12. classify replies;
13. notify the founder only on meaningful interest or exceptions;
14. append an immutable action receipt.

---

## 2. Default operating mode

The default is:

```text
NETWORKING_ONLY
```

Allowed:

- request an introduction;
- ask whether the thesis fits the person's investment/strategic interests;
- offer the public business plan;
- discuss robotics, venues, sponsorship and partnership;
- request a meeting;
- collect non-binding interest.

Blocked:

- offering shares;
- quoting valuation or investment price;
- accepting money;
- promising returns;
- representing projected revenue as fact;
- using fabricated traction, contacts or investor commitments.

Actual investment terms unlock only after counsel approves an offering pathway and the campaign config records that approval.

---

## 3. Compliance state machine

```text
SPONSOR_ONLY
NETWORKING_ONLY
PRE_OFFER_RESEARCH
REG_CF_TEST_WATERS
REG_CF_LIVE
REG_D_506C_LIVE
LEGAL_HOLD
```

### Guard rule

```pseudo
if message.contains_investment_terms:
    require campaign.mode in {REG_CF_TEST_WATERS, REG_CF_LIVE, REG_D_506C_LIVE}
    require campaign.counsel_approval_hash != null
    require campaign.approval_timestamp != null
    require compliance_template_for(campaign.mode)
else:
    continue
```

For `REG_CF_LIVE`, investment execution must route to the selected registered intermediary; the local system does not create a private checkout page.

For `REG_D_506C_LIVE`, the system may support permitted general-solicitation outreach only after legal configuration; actual purchasers still require accredited-investor verification through an approved process.

---

## 4. Architecture

```text
┌────────────────────────────┐
│      Founder Dashboard      │
│ [RUN] [PAUSE] [LEGAL HOLD] │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│       Campaign Kernel       │
│ state / budgets / limits    │
└──────┬────────┬────────────┘
       │        │
       │        └───────────────┐
       ▼                        ▼
┌─────────────┐          ┌──────────────┐
│ Prospector  │          │ Reply Monitor│
└─────┬───────┘          └──────┬───────┘
      ▼                         ▼
┌─────────────┐          ┌──────────────┐
│ Enrichment  │          │ Classifier   │
└─────┬───────┘          └──────┬───────┘
      ▼                         ▼
┌─────────────┐          ┌──────────────┐
│ Fit Scorer  │          │ Alert Engine │
└─────┬───────┘          └──────────────┘
      ▼
┌─────────────┐
│ Message Gen │
└─────┬───────┘
      ▼
┌────────────────────────────┐
│    Compliance Governor      │
│ suppression / claims / mode │
└─────────────┬──────────────┘
              ▼
        Gmail API Sender
              │
              ▼
       Receipt / Audit Log
```

---

## 5. Local-first implementation

### Recommended stack

- Python 3.12+
- SQLite
- standard-library `sqlite3`
- Gmail API OAuth for outbound/reply monitoring
- optional local Ollama model for message/reply classification
- deterministic rule fallback if no local model is available
- Brave Search API / Serper / another explicitly configured search API for prospect discovery
- plain HTML local dashboard or lightweight FastAPI only if remote control is later required

Avoid expensive CRM dependencies during validation.

### Repository shape

```text
capital-engine/
  pyproject.toml
  README.md
  config.example.toml
  capital_engine/
    __main__.py
    config.py
    db.py
    models.py
    prospect.py
    enrich.py
    score.py
    compose.py
    compliance.py
    gmail_client.py
    replies.py
    alerts.py
    receipts.py
    dashboard.py
  migrations/
    001_init.sql
  templates/
    networking_intro.txt
    sponsor_intro.txt
    venue_intro.txt
    robot_partner_intro.txt
  tests/
    test_score.py
    test_compliance.py
    test_suppression.py
    test_reply_classifier.py
```

---

## 6. SQLite schema

```sql
CREATE TABLE prospects (
  id INTEGER PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  organization TEXT,
  prospect_type TEXT NOT NULL,
  website TEXT,
  email TEXT,
  stage TEXT NOT NULL DEFAULT 'DISCOVERED',
  fit_score INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(canonical_name, organization)
);

CREATE TABLE prospect_evidence (
  id INTEGER PRIMARY KEY,
  prospect_id INTEGER NOT NULL,
  source_url TEXT NOT NULL,
  source_title TEXT,
  evidence_text TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  FOREIGN KEY(prospect_id) REFERENCES prospects(id)
);

CREATE TABLE campaigns (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  mode TEXT NOT NULL,
  counsel_approval_hash TEXT,
  approval_timestamp TEXT,
  daily_send_limit INTEGER NOT NULL DEFAULT 15,
  active INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER NOT NULL,
  prospect_id INTEGER NOT NULL,
  direction TEXT NOT NULL,
  subject TEXT,
  body TEXT NOT NULL,
  status TEXT NOT NULL,
  provider_message_id TEXT,
  sent_at TEXT,
  FOREIGN KEY(campaign_id) REFERENCES campaigns(id),
  FOREIGN KEY(prospect_id) REFERENCES prospects(id)
);

CREATE TABLE replies (
  id INTEGER PRIMARY KEY,
  message_id INTEGER,
  prospect_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  interest_score INTEGER NOT NULL,
  classification TEXT NOT NULL,
  received_at TEXT NOT NULL,
  FOREIGN KEY(message_id) REFERENCES messages(id),
  FOREIGN KEY(prospect_id) REFERENCES prospects(id)
);

CREATE TABLE suppression_list (
  email TEXT PRIMARY KEY,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE compliance_events (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER,
  event_type TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE receipts (
  id INTEGER PRIMARY KEY,
  action_type TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  previous_receipt_sha256 TEXT,
  receipt_sha256 TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
```

---

## 7. Prospect categories

### Tier A — strategic capital/resource partners

Highest value because they can reduce capital requirements.

- humanoid manufacturers;
- robotics integrators;
- venue operators;
- hospitality/nightlife groups;
- event production companies;
- experiential-marketing agencies;
- sponsors with technology/nightlife fit.

### Tier B — investors

- robotics angels;
- AI angels;
- entertainment-tech investors;
- hospitality investors;
- pre-seed/micro-VC;
- strategic family offices;
- funds with physical-AI or experiential-entertainment thesis.

### Tier C — public/crowdfunding audience

Only activated after legal pathway/intermediary selection.

---

## 8. Discovery query library

Example search intents:

```text
"robotics angel investor" humanoid
"physical AI" venture fund seed
"entertainment technology" angel investor
"experiential entertainment" venture capital
"hospitality technology" seed fund
"nightlife" investor hospitality group
humanoid robot distributor USA
humanoid robot integrator United States
robotics sponsor experiential marketing
nightclub group innovation partnerships
```

For every candidate, capture evidence showing **why** the prospect fits. A search result alone is not sufficient.

---

## 9. Deterministic fit score

```text
thesis_fit          0–25
stage_fit           0–20
check_size_fit      0–15
portfolio_adjacency 0–15
geography           0–10
recent_activity     0–10
verified_contact    0–5
-------------------------
TOTAL               0–100
```

Suggested policy:

```text
0–49   archive / low priority
50–64  research queue
65–79  personalized outreach queue
80–100 founder-priority queue
```

Never allow an LLM to directly assign the final score without preserving the underlying evidence fields.

---

## 10. Reply classifier

Output schema:

```json
{
  "interest_score": 0,
  "classification": "NOT_INTERESTED|INFO_REQUEST|MEETING_REQUEST|STRATEGIC_INTEREST|INVESTMENT_INTEREST|LEGAL_OR_COMPLIANCE|UNSUBSCRIBE|OTHER",
  "evidence": [],
  "next_action": "",
  "needs_founder": false
}
```

### Founder notification threshold

Notify immediately when:

- `interest_score >= 75`;
- meeting requested;
- deck/data-room requested;
- terms/valuation/check-size requested;
- hardware/venue/sponsor resource offered;
- legal/compliance issue raised;
- high-value prospect replies unexpectedly.

Do not notify for:

- out-of-office;
- generic rejection;
- newsletters;
- obvious automated responses;
- unsubscribe acknowledgments.

---

## 11. Gmail workflow

Create labels:

```text
AIAD/Investors
AIAD/Partners
AIAD/Interested
AIAD/Meeting
AIAD/NoFit
AIAD/Unsubscribe
```

Outbound message records store the Gmail message/thread identifier. Replies are mapped to the originating prospect so the system never guesses who responded.

### Safety rule

An unsubscribe signal immediately:

1. inserts address in `suppression_list`;
2. cancels queued outbound messages;
3. writes a compliance receipt;
4. prevents future campaign insertion.

---

## 12. CAN-SPAM baseline

Commercial outreach should be built to satisfy the FTC baseline, including:

- accurate sender/header identity;
- non-deceptive subjects;
- required ad/solicitation identification where applicable;
- valid postal address;
- clear opt-out mechanism;
- prompt honoring of opt-out requests.

The FTC states CAN-SPAM applies to B2B commercial email too. If a message contains sexually oriented commercial material, the Adult Labeling Rule needs separate review. The cleanest investor outreach should remain factual and non-explicit: “AI-native robotic live entertainment” rather than sending sexual imagery/material in cold email.

---

## 13. Daily send policy

Start small:

```text
Days 1–7:   max 10/day
Days 8–14:  max 15/day
After 14d:  max 20/day unless deliverability metrics justify more
```

Stop automatically if:

- bounce rate > 5%;
- unsubscribe rate > 2% over rolling 100 messages;
- provider warning occurs;
- complaint signal occurs;
- campaign enters `LEGAL_HOLD`.

Quality beats volume. Twenty researched messages are worth more than 2,000 shitty scraped emails.

---

## 14. Founder dashboard

Minimum UI:

```text
AI AFTER DARK — CAPITAL ENGINE

MODE: NETWORKING_ONLY
STATUS: READY

[ RUN CAMPAIGN ] [ PAUSE ] [ LEGAL HOLD ]

New prospects today:       18
Qualified >=65:             7
Messages sent:             10
Replies:                    3
High-interest replies:      1
Meetings requested:         1
Suppressed:                 0

HOT LEAD
------------------------------------------------
Name / organization
Score: 91
Why fit: physical-AI investor + seed-stage + recent humanoid deal
Reply: requests 20-minute meeting and deck
[OPEN THREAD] [CREATE RESPONSE] [MARK DILIGENCE]
```

---

## 15. Automation phases

### Phase 1 — Safe autonomous prospecting

Build first:

- SQLite CRM;
- search adapter;
- evidence capture;
- dedupe;
- scoring;
- report generation.

No outbound sending required.

### Phase 2 — Draft-only outreach

System writes Gmail drafts. Founder reviews/sends.

### Phase 3 — Auto-send networking

Only verified prospects scoring above threshold; strict daily limits; compliance footer; suppression system.

### Phase 4 — Reply monitoring and alerts

Inbox polling/classification becomes automatic.

### Phase 5 — Legally enabled capital mode

After counsel + offering configuration, enable the exact message templates and routing rules approved for Reg CF or 506(c).

---

## 16. Zero-capital execution stack

A first useful version can run largely on owned/local infrastructure:

- SQLite: free;
- Python: free;
- Gmail API: no CRM subscription required;
- local LLM through Ollama: optional/free if hardware supports it;
- public investor/firm websites: research source;
- one low-cost/free-tier search API if necessary;
- GitHub: source control;
- existing website: investor packet distribution.

Paid data providers such as PitchBook/Crunchbase should be optional enrichers, not architectural dependencies.

---

## 17. Verification tests

The engine is not complete until it passes:

1. duplicate prospect test;
2. fabricated-email rejection test;
3. missing-source rejection test;
4. unsubscribe suppression test;
5. legal-hold test;
6. unauthorized investment-terms test;
7. send-limit test;
8. bounced-address quarantine test;
9. reply-thread mapping test;
10. high-interest alert test;
11. false-positive auto-reply test;
12. restart/recovery test;
13. receipt hash-chain test;
14. local-model unavailable fallback test.

### Critical invariant

> **The system may automate discovery, prioritization and permitted communication. It may never manufacture evidence, silently alter the legal offering mode, or accept investor money outside the approved transaction path.**

---

## 18. Highest-leverage build order

1. Create `capital.db` and schema.
2. Implement prospect ingestion + evidence hashing.
3. Implement deterministic scoring.
4. Implement dashboard/report.
5. Connect Gmail in draft-only mode.
6. Add reply monitoring.
7. Add notification threshold.
8. Add outbound auto-send after suppression/CAN-SPAM controls pass tests.
9. Add search/enrichment adapters.
10. Keep securities-specific modes locked until legal approval.

This produces a useful engine early instead of spending weeks building a giant CRM before one prospect exists.

---

## 19. External legal/regulatory references

- SEC Reg CF issuer guidance: https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/regulation-crowdfunding-guidance-issuers
- SEC Rule 506(c): https://www.sec.gov/resources-small-businesses/exempt-offerings/general-solicitation-rule-506c
- SEC offering pathways: https://www.sec.gov/resources-small-businesses/capital-raising-building-blocks/offering-pathways
- FINRA funding portals: https://www.finra.org/registration-exams-ce/funding-portals
- FTC CAN-SPAM guide: https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business
