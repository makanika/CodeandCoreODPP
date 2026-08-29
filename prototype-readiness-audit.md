# ODPP Prototype Readiness Audit

## Audit Position

The project has a coherent prototype definition. It is a scale model of the production system: it must prove the full custody, complaint, routing, access-control, SLA, and audit behaviour on a small fictional pilot dataset before ODPP commits to regional or national rollout.

The prototype is **not yet fully scope-locked**. The items in the decision register must be resolved before implementation starts, because they change data access, routing, or acceptance testing.

## Confirmed Prototype Contract

The following is understood and should be demonstrated end to end.

| Area | Prototype behaviour to prove |
| --- | --- |
| Pilot footprint | Jinja Road, Masaka CPS, and Arua CPS, with the assigned regional ODPP chain and HQ escalation. |
| Case identity | One canonical case reconciles SD/OB, CRB, ODPP, and court references as they become available. |
| Custody | Every dispatch, receipt, return, allocation, and correction is an append-only movement event with timestamp, actor, source, and destination. |
| Case decisions | Perusal creates durable sanction, DFI, or closure minutes; previous decisions are never overwritten. |
| Assisted lodging | Designated police terminals create a case reference, one-time PIN, printable receipt, and opaque QR locator. |
| Complaint intake | Public portal, assisted/walk-in desk, toll-free capture, and monitored email write to one intake schema. |
| Complaint anchor | Intake binds to CRB; where no CRB is supplied, staff resolve it from the station ledger before routing advances. |
| Process complaint | Routes to RSA, automatically escalates to Regional Officer when its SLA expires, and escalates to HQ/DPP on second expiry or recorded dissatisfaction. |
| Conduct complaint | Bypasses the station and routes to HQ Inspections/IQA. The subject officer has no view, edit, export, or search access. |
| SLA and escalation | Clocks are calculated in the background. Escalation is automatic and an immutable ledger event, not a discretionary reminder. |
| Documents | Demonstrate controlled upload, scan/OCR queue, metadata, searchable indexing, and access-bound downloads for redacted docket artefacts. |
| Access control | Demonstrate scoped datasets and denied access logging for every role. Test direct query/export boundaries, not only page visibility. |
| Dashboards and reports | Role-specific queues, DPP/Deputy national operational dashboard, SLA flags, audit views, and scope-aware PDF reports. |
| Demo dataset | Fictional `DEMO` staff, officer/service numbers, stations, cases at all pipeline stages, closed cases, Type A and Type B complaints, reassignments, risks, breaches, and closure paths. |
| Pilot mode | Run alongside paper procedures. Start with a constrained regional pilot, not a national switch-over. |

## Required Demonstration Journeys

The POC should be accepted only after it demonstrates all of these journeys with saved audit evidence.

1. **Case-to-court chain:** officer records SD/CRB, dispatches file, registry receives it, RSA peruses it, a perusal minute is recorded, and a court reference is attached.
2. **Lost-custody signal:** a dispatch remains unreceived beyond threshold, is shown as stalled, is escalated, then is corrected through a new event without deleting the original dispatch.
3. **Process-complaint escalation:** citizen submits or staff records a CRB-linked complaint, it opens with the RSA, breaches the working SLA, auto-escalates to the regional officer, and reaches an HQ directive if still unresolved.
4. **Conduct isolation:** a complaint against an RSA/IO bypasses the local station, creates a sealed record, blocks the subject officer from list, detail, search, export, and download actions, and logs every allowed/denied access attempt.
5. **Reassignment:** an authorised user reassigns a case or Type B complaint with a reason; prior owner, SLA, and breach state remain in the timeline.
6. **Public boundary:** tracker accepts only valid reference/PIN or tracking-code verification and returns no narrative, names, file location, attachment, or detailed case stage.
7. **Document and OCR path:** a redacted charge sheet, Police Form 3, and perusal minute upload to an async scan/index queue, become searchable when processing completes, and remain access controlled.
8. **Reporting boundary:** generate a scoped PDF queue or latency report and confirm that excluded records and sealed conduct material do not appear.

## Gaps to Add to the Build Brief

### 1. Four-channel intake and channel-specific evidence

The brief currently specifies public web submission and staff intake. It must explicitly add the four source channels used in the process reference:

- public portal;
- toll-free/call-centre capture console;
- walk-in or assisted desk;
- monitored email intake.

Each intake record needs `channel`, `received_at`, `captured_by`, source/forwarding evidence, and acknowledgement outcome. All channels must create the same complaint schema and tracking response.

### 2. OCR, indexing, and safe search

The source process requires an asynchronous scan and OCR queue for redacted dockets. Add:

- upload state: queued, scanning, indexed, failed, quarantined;
- retry and failure handling;
- extracted-text storage and confidence score;
- permitted full-text fields: CRB, ODPP reference, party name, and charge where approved;
- object-level search filtering before results, snippets, export, and autocomplete are returned;
- a manual verification step for OCR-derived reference links.

OCR is a POC capability, not a replacement for a verified human record.

### 3. Explicit Type B routing state machine

The brief's generic Type B lifecycle must be reconciled with the source routing states. For the POC, define the canonical mapping:

`RECEIVED -> OPEN_RSA -> RESOLVED_RSA | ESCALATED_REGIONAL -> RESOLVED_REGIONAL | ESCALATED_HQ -> REINSTATED | SANCTIONED`

The Type B communication and closure records may remain additional lifecycle metadata, but they must not obscure the automatic RSA-to-region-to-HQ routing and the approved SLA clocks. Reopening a resolved complaint must create a new linked complaint, not reopen and overwrite the original.

### 4. HQ directives and File Recall Orders

Add a `FileRecallOrder` or equivalent immutable directive record for the HQ path. It needs issuer, authority, date, linked case/complaint, stated directive, target custodian, required return/response date, and acknowledgement. The resulting master case state must become `REINSTATED` or `SANCTIONED` as authorised.

### 5. One authoritative data model and field dictionary

The brief names core models but does not yet give a minimum shared field dictionary. Before build, approve field definitions and controlled values for:

- party/complainant identity and contact;
- SD/OB, CRB, ODPP, and court reference normalisation;
- offence/charge identifiers;
- station, region, physical and digital location;
- custody, courier, receipt, allocation, and expected-action date;
- complaint category, allegation, subject officer, channel, tracking code/PIN;
- assignment, priority, SLA target, suspension reason, escalation event, and directive;
- attachment classification, OCR state, and redaction status;
- audit event, actor, reason, source IP/device, and before/after values.

### 6. Seed-data manifest and account matrix

The brief requires seed data but should include a reproducible `seed-data-manifest` that lists every fictional user, role, scope, station, regional routing, reference, case stage, complaint stage, document, and expected dashboard count. This becomes the demo script and regression fixture.

The current 18-day workplan displays **11 owners** but lists **12 people**. Resolve this count before the roadmap is treated as a governed plan.

### 7. Acceptance evidence and security test log

The POC needs test artefacts, not just automated tests:

- role/action/scope matrix signed by the ODPP owner;
- a saved denied-access log for conduct recusal and cross-station access attempts;
- screenshot or PDF evidence of queue, SLA, and escalation states;
- test results for invalid PIN/tracking combinations and rate limits;
- test report for PDF/export filtering;
- pilot runbook, support contacts, backup/restore result, and rollback procedure.

## Material Decisions to Resolve

| Decision | Why it matters | Recommended position for the POC |
| --- | --- | --- |
| DPP/Deputy access to sealed Type A narrative | The supplied case-pipeline prototype says DPP cannot read sealed conduct narratives; the current brief grants the DPP and authorised Deputy DPP read-only conduct oversight. These cannot both be true. | Preserve the prototype's default-deny design. Give DPP/Deputy aggregate counts and escalation metadata only, then require a documented exceptional-access policy before revealing a narrative. |
| Pilot geography | Source material recommends one region first; the brief requires three stations across three locations. | Treat three stations as the demonstration dataset, but run the operational paper-parallel pilot in one confirmed region first. |
| Tracking credential | Source flow says a complaint tracking code; the brief uses reference + six-digit PIN and case-lodging QR receipt. | Keep reference + PIN for public privacy. Define whether the QR locator starts a complaint, verifies a receipt, or pre-fills a reference; do not make it a bearer credential. |
| Type B SLA | Source routing uses an assumed 7-day RSA window; brief names generic SLA targets. | Seed and demonstrate 7 working days as a clearly labelled POC assumption, with thresholds configurable and approval required for production. |
| Type A storage and handoff | Separate conduct database is specified, but exact transfer fields and classification reversal remain unresolved. | Create a minimal sanitised handoff contract and prohibit reverse replication. Confirm final policy before production. |
| Terminals and devices | Assisted police terminals appear in the brief, but hardware, offline behaviour, printer, QR scanner, and support are not defined. | Demonstrate one browser-based terminal workflow with a printer-friendly receipt. Treat hardware rollout and offline synchronisation as production design work. |
| External integrations | SMS/email, OCR engine, malware scan, object storage, backup, and official station directory providers are undecided. | Use mock/adaptor interfaces for the POC, with a visible integration-status screen and no production credentials. |

## Recommended Scope Boundary

### In the 18-day POC

- Browser-based Django demonstration stack.
- Fictional seed data for the required three-station chain.
- One complete process complaint journey and one sealed conduct denial test.
- Case movement, perusal decision, reassignment, SLA clock/auto-escalation, role queues, document upload, asynchronous OCR demonstration, audit log, and PDF report.
- Public tracker with safe reference/PIN behaviour.
- Offline/local demonstration deployment that does not require ODPP production-network access.

### In the 13-week production build and pilot

- Final policy, data-protection, retention, and lawful-hold approval.
- Real directory/station data, signed role matrix, official forms, document taxonomy, and approved templates.
- Real notification, OCR, malware scanning, storage, monitoring, backup, and identity integrations.
- Security testing, UAT, training, operations runbook, service support model, and paper-parallel pilot.
- One-region operational pilot before any national deployment.

## Conclusion

The underlying design is sound for a wind-tunnel prototype. The scale model must prove failure modes, not only screens: a file that goes missing, an SLA that auto-escalates, a wrong user denied access, a sealed allegation isolated from its subject, and a citizen receiving a safe status update. Once the decision register is resolved and the eight demonstration journeys run reliably, the system has a credible basis for controlled scaling.
