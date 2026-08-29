# ODPP Case Pipeline and Complaints Console

## 1. Purpose

Build a Django monolith for the Office of the Director of Public Prosecutions (ODPP). It follows criminal case files through police and ODPP handling and manages complaints about case handling.

The build follows the ODPP Case Pipeline Prototype as its operational and UX reference:

- two entry points: a minimal public complaint tracker and an authenticated staff console;
- custody and movement tracking without public exposure of case narrative;
- role-, region-, station-, custody-, and allocation-based access;
- a sealed Type A conduct workflow isolated from ordinary case-process complaints;
- queues, timelines, and analytics for operational supervision.

The proof-of-concept uses fictional `DEMO` data across Jinja Road Police Station, Masaka Central Police Station (CPS), and Arua CPS, with their corresponding ODPP registries and regional-to-HQ routing. The controlled operational pilot runs paper-parallel in one ODPP region after UAT and ODPP approval; it is not a national switch-over.

## 1.1 Client Context and Product Position

ODPP is a public prosecution institution. This system supports the internal work of receiving, assigning, prosecuting, supervising, and quality-assuring criminal case files; it is not a public portal for discovering case outcomes or reading prosecution records.

The interface, workflow labels, and reporting structure must reflect the client organisation's functional shape:

- prosecution work is handled through regional intake, registry custody, and allocated legal officers;
- management-support functions need national operational oversight without ordinary access to all case content;
- IQA, research, and training functions need aggregated quality, delay, and trend information;
- specialised directorates and departments may require scoped operational workspaces, but are not automatically granted conduct-narrative access;
- the public needs a clear, respectful route for lodging and tracking a service complaint, rather than a detailed case-information service.

Use ODPP's published public-facing language and approved visual identity when those assets and wording are supplied by the client. Do not infer official policy, legal advice, office addresses, or a service promise from the website alone; each must be approved before release.

## 2. Security Boundaries

### Public boundary

The public can lodge a complaint and track it using a reference and PIN. Tracking returns only a plain-language complaint status and next step. It must never disclose officer identities, case narrative, file location, detailed pipeline stage, attachments, internal notes, or complaint evidence.

### Staff boundary

Staff access is allowed only when both role permission and scope permit the action. Scope may be national, regional, station-based, registry-custody-based, or a direct case allocation. Denied access attempts are audited.

### Type A conduct boundary

Type A complaints alleging staff misconduct are held in a separate `conduct` database. The primary database must not retain the sealed allegation narrative or Type A evidence. The conduct database uses immutable reference values or actor identity snapshots rather than foreign keys to the primary database.

The DPP and Deputy DPP accounts have national operational oversight and see aggregate conduct volumes and escalation metadata where needed, but cannot read sealed Type A conduct narratives or evidence. A subject officer cannot discover or access a conduct file naming them. Every conduct list, view, edit, download, export, and denied access attempt is audited.

## 3. Roles, Hierarchy, and Scope

Use a custom Django `StaffUser` model from the first migration. `StaffUser.role` is a strict enum. Do not rely on one nullable `region` and `station` field alone: national access, multiple regional/station assignments, registry custody, and individual case allocations require explicit scope relationships.

| Layer | System role | Operational responsibility | Default scope |
| --- | --- | --- | --- |
| Police station | Investigating Officer (IO) | Opens SD/CRB record and updates police-side movement | Own police station |
| Police station | OC Station / Station Supervisor | Confirms dispatch and handover integrity | Own police station |
| Police station | Police Liaison (external) | Sees status and custody of own station files, without narratives or complaints | Own police station, read-only |
| ODPP regional intake | Registry Clerk | Receives files and creates or links ODPP references | Assigned regional registry |
| ODPP central intake | Registry Officer | Moves files between registries and flags custody issues | National registry |
| ODPP prosecution | Resident State Attorney (RSA) | Perusal, sanction, DFI, and closure direction | Allocated cases only |
| ODPP supervision | Regional Inspectorate Officer | Monitors Type B SLAs and escalates delays | Assigned ODPP region |
| ODPP complaints | Head of Complaints | Classifies Type A/B and controls complaint workflow | National |
| ODPP conduct | Internal Affairs Officer | Handles sealed Type A conduct files | Conduct scope only |
| ODPP executive | DPP / Deputy DPP | National operational oversight, policy escalation, and analytics | National, without sealed conduct narrative or evidence |
| ODPP executive | Directorate Head | Operational oversight, policy escalation, and analytics | National, without sealed narratives |

The hierarchy must also accommodate ODPP leadership functions visible in the organisation structure: Deputy DPP (International Affairs), Deputy DPP (Management Support Services), Deputy DPP (IQA/Research/Training), Head of Prosecutions Directorate, and department leads such as International Cooperation & Asset Recovery and International Crimes. Unless approved otherwise, these are executive/oversight roles and receive analytics or operational summaries rather than automatic access to sealed conduct material.

Create and approve an action matrix for every role and scope. It must cover `list`, `view`, `create`, `edit`, `transition`, `assign`, `move`, `upload`, `download`, `export`, `search`, and `view_analytics`. Enforce it in views, APIs, Django admin, search, exports, downloads, and background jobs.

## 4. Case Pipeline

### Case record

`CaseReference` is the primary tracked-case record. It stores structured and validated police SD, CRB, ODPP, and court identifiers. Each identifier records its reference type, issuing institution, value, and uniqueness rule.

A case stores its current stage, police station, ODPP region, current registry holder where applicable, allocated prosecutor where applicable, and an append-only movement history.

### Police-assisted case lodging and receipt

At designated assisted-lodging terminals at Jinja Road, Masaka CPS, and Arua CPS, a police officer registers a new case with the complainant or case holder present. The POC demonstrates this as a browser-based workflow with a printer-friendly receipt; offline synchronisation, terminal hardware, and QR-scanner procurement belong to the production design. The system generates a unique case reference, a six-digit PIN, and a printable receipt containing a QR code.

The receipt identifies the lodging station, lodging date/time, case reference, and officer identity or officer number. The PIN is shown only on this receipt and stored only as a secure hash. The QR code encodes an opaque, non-sensitive receipt-verification and complaint-lodging locator. It must not contain the PIN, case narrative, officer identity, attachment links, or a bearer credential. Scanning it may prefill the case reference for a secure public action, but must not reveal the detailed case pipeline.

The terminal workflow requires the logging-in officer to confirm the entered information with the person present, print or display the receipt once, and create an audit event recording the terminal, station, officer, and receipt issuance. Reissue, correction, and lost-PIN support need separate privileged flows and audit records.

### Pipeline stages

Initial stages:

`POLICE_OPENED -> POLICE_PREPARING -> DISPATCHED_TO_ODPP -> ODPP_RECEIVED -> UNDER_PERUSAL -> DFI_ISSUED | SANCTIONED -> BEFORE_COURT -> CLOSED`

Define a transition table for each stage: permitted actor role, prerequisite data, resulting status, required note/document, and whether it creates a `FileMovement`. A transition must never rewrite historical movement.

### File movement

`FileMovement` forms an immutable chain of custody. It records sending and receiving institution, actor, timestamp in `Africa/Kampala`, movement type, declared contents, receipt acknowledgement, and an optional correction link. A correction creates a new event and retains the original.

Movement types include dispatch, receipt, internal transfer, return for action, court transfer, and closure/archival. Lost or disputed custody is an exception state, never deletion of history.

### Reassignment, queues, and SLA flags

Cases and Type B complaints can be reassigned in the style of a ticketing system. An authorised supervisor or registry role selects a new owner or queue, records a mandatory reason, and may set a due date and priority. The original assignment, reassignment actor, time, reason, and SLA history remain visible in the audit timeline.

The system flags SLA risk before breach and flags overdue work after breach. It must show distinct indicators for unassigned, due soon, overdue, stalled pending receipt, and escalated work. Reassignment never clears an existing breach, stops the SLA clock, or changes historical ownership. Type A assignment and reassignment use the separate conduct workflow and audit boundary.

Seed the authoritative station-to-region mapping for Jinja Road, Masaka CPS, and Arua CPS. Use it for scope checks, intake, queues, reporting, and demonstration data.

## 5. Complaints Workflow

### Public submission and tracking

All intake channels write to one complaint schema and generate the same acknowledgement/tracking outcome. The POC supports:

- `/complain/`: multi-step complaint form for contact details, complaint details, related case references, and evidence;
- toll-free/call-centre capture console;
- walk-in or assisted-desk capture;
- monitored-email intake;
- `/complain/done/`: one-time receipt showing CMP reference and six-digit PIN, with printable receipt;
- `/track/`: reference-and-PIN status tracker;
- `/offices/`: ODPP office directory.

Generate a unique `CMP/<YEAR>/<SEQUENCE>` reference. Store the PIN only as a secure hash and never show it after the receipt page. Record intake channel, received time, capturing officer, and source/forwarding evidence. Rate-limit submission and tracking. Invalid reference/PIN responses must not reveal whether either value exists.

The public form and receipt must present privacy and lawful-processing information plus an accessible assistance route. Attachment rules must define permitted types, maximum size, malware scanning, storage, and retention.

### Type B case-process complaints

Type B complaints concern delay, file handling, communication, or other case-process issues. Where the complainant has no CRB reference, triage resolves it against the station ledger before routing advances. Their routing lifecycle is:

`RECEIVED -> OPEN_RSA -> RESOLVED_RSA | ESCALATED_REGIONAL -> RESOLVED_REGIONAL | ESCALATED_HQ -> REINSTATED | SANCTIONED`

The complaint record also captures acknowledgement, classification, assignment, inquiry, determination, and communication events. `WITHDRAWN` and `REFERRED_OUT` are valid terminal paths. A resolution cannot close until communication records the approved channel, recipient, date, outcome, and supporting evidence where appropriate. Reopening creates a new linked complaint; it never overwrites a resolved complaint.

The RSA receives the first process complaint. On SLA expiry or recorded dissatisfaction, the system automatically escalates it to the responsible Regional Officer. On a second expiry or dissatisfaction, it escalates to HQ/DPP, where a binding directive is recorded.

### Type A conduct complaints

The Head of Complaints classifies an unclassified complaint as Type A or Type B. On Type A classification, create a `ConductComplaint` in the conduct database with `IAF/<YEAR>/<SEQUENCE>`, transfer only minimum identifiers, seal the narrative, and write an audit event.

ODPP must approve the Type A state machine, reassignment rules, disposition categories, and reclassification policy before production. Until that approval, sealed Type A narratives and evidence must not flow back into the primary database.

### SLA rules

Complaint age and case dwell time are distinct. For the POC, the RSA process-complaint window is seven working days, visibly marked as an ODPP approval assumption. The threshold is configurable. Use `Africa/Kampala`; production approval sets the working-day calendar, holiday source, acknowledgement target, overdue bands, escalation recipients, and final timing. Type B supervisors see the next required escalation action; the public does not.

### HQ directives

`FileRecallOrder` is an immutable HQ directive record. It includes issuer, authority, date, linked case and complaint, directive text, target custodian, required response date, and acknowledgement. A valid HQ directive may set the master case outcome to `REINSTATED` or `SANCTIONED`; it always creates an audit and ledger event.

## 6. Staff Console

Routes:

- `/dashboard/`: role-routed landing page;
- `/desk/`: SLA-prioritized queue;
- `/desk/intake/`: registry intake for letters and walk-ins;
- `/desk/triage/`: classification into Type A or Type B;
- `/desk/<pk>/`: staff complaint detail and timeline;
- `/desk/<pk>/determine/`: findings and remedy capture;
- `/desk/<pk>/communicate/`: mandatory communication proof;
- `/pipeline/`: staff-only case timeline and movement view;
- `/conduct/` and `/conduct/<pk>/`: restricted conduct views;
- `/insight/latency/`: internal executive analytics;
- `/insight/published/`: approved public quarterly aggregates.

Excluded users must not receive information that reveals a sealed conduct allegation exists.

## 6.1 Prototype Target: Django Screens and Behaviour

The Django application should be a purposeful operational console, not a generic government website or marketing landing page.

### Entry screen

The first screen presents an ODPP masthead, the product name **Case Pipeline & Complaints Console**, and two equal, distinct routes:

- **Officer sign-in** opens the authenticated operational console;
- **Public complaint tracker** opens complaint submission and reference/PIN tracking only.

The public route must not contain case search, pipeline views, staff directory information, or a link that reveals authenticated routes.

### Authenticated shell

The officer console uses a compact government-service layout: ODPP identity in the header, current user and scope, sign-out control, persistent navigation, and a clear environment banner outside production. Navigation appears only for permitted modules.

After sign-in, users land on their relevant workspace rather than a universal dashboard:

| User function | Default workspace |
| --- | --- |
| Police IO / OC Station | Station case and dispatch queue |
| Police Liaison | Read-only station custody/status queue |
| Registry Clerk / Registry Officer | Intake, receipt, and movement queue |
| Resident State Attorney | My allocated cases and perusal actions |
| Regional Inspectorate | Type B overdue, SLA, and escalation queue |
| Head of Complaints | Unclassified complaints and classification workload |
| Internal Affairs Officer | Sealed conduct queue only |
| DPP / Deputy DPP | National executive dashboard, all operational queues, reports, and aggregate conduct oversight only |
| Directorate or departmental lead | Role-scoped operational dashboard and analytics |

### Operational views

The case folder page is the core staff screen. It has a stable case-reference header; visible current status and custodian; an ordered movement timeline; stage actions gated by role; documents and evidence subject to access rules; linked Type B complaint indicators where allowed; reassignment history; SLA indicators; and a local audit/history tab. It must not expose sealed Type A existence to excluded users.

The queue view prioritises work by SLA, dwell time, pending receipt, assignment, and escalation status. It supports only authorised filters such as station, region, stage, case owner, and overdue band. Result counts and export capability are scope-limited.

The complaint workspace presents a chronological timeline, classification, assignment, inquiry actions, determination, and communication proof. The Type A workspace is visually and technically separate, carries a sealed-file indicator, and does not share normal complaint search or export surfaces.

### Executive and public views

Every role receives a dashboard appropriate to its permitted work. Dashboards show only records and counts within the user's scope, with workload, queue age, SLA-risk/overdue flags, pending receipt, unassigned items, and recent movement where permitted. The DPP and Deputy DPP receive national operational dashboards and full operational drill-down. Sealed conduct dashboards disclose aggregate counts and escalation metadata only, never narrative or evidence.

Executive views use concise tables and charts for volumes, movement delay, queue age, regional comparison, reassignment volume, and escalation. They provide drill-down only when the user's scope allows it. The public quarterly view presents approved aggregate measures only.

The public tracker is deliberately calm and sparse: reference/PIN form, status, next step, date of last meaningful update, and contact/escalation guidance approved by ODPP. It never displays an internal timeline, officer name, attachment, or case-file location.

## 7. Evidence, Audit, and Records

Evidence metadata records uploader, timestamp, original filename, file type, size, malware-scan result, private storage key, content hash, visibility classification, and retention disposition. Files are stored in private object storage. Every download requires authorization and an audit entry.

### Case-file uploads

Support controlled upload categories for the police-to-ODPP-to-court file. The initial demonstration set includes:

- police station diary or occurrence-book (SD/OB) reference and investigation-file cover/docket;
- investigation diary, witness statement, exhibit register, seizure/search memo, arrest report, and supplementary report;
- charge sheet and police bond or recognizance;
- ODPP sanction to prosecute, prosecution decision, or DFI;
- committal papers, indictment or information, and court warrants, orders, rulings, or judgment.

These are file categories, not a claim that every underlying template is nationally uniform. Before production, ODPP, Uganda Police, and Judiciary stakeholders must approve the official document names, mandatory metadata, file-naming convention, redaction rules, and which police records are permissible to upload. Witness, medical, and sensitive investigative material must receive a restrictive visibility classification by default.

Uploads are scanned asynchronously. Each document has an ingestion status of `QUEUED`, `SCANNING`, `INDEXED`, `FAILED`, or `QUARANTINED`, plus retry history, malware result, OCR confidence, and a manual-verification flag. The POC indexes approved redacted charge sheets, Police Form 3 documents, and perusal minutes for permitted full-text search. Search filtering is applied before results, snippets, autocomplete, export, or download are returned.

### Seed records and demonstration data

Seed believable, clearly fictional demonstration data for each pilot location and its ODPP regional chain from station to headquarters. Include fictional names and officer/service numbers for every actor at each stage: IO, OC Station, police liaison, registry staff, RSA, inspectorate, complaints, internal affairs, and executive oversight. Seed data must be visibly marked `DEMO` and must not reuse real staff identities or service numbers.

The seed pack must include cases at every pipeline stage; cases closed without complaints; cases with Type B complaints at different stages; Type A examples accessible only through conduct permissions; and complaints lodged, assigned, investigated, determined, communicated, and closed through the system. It must also include pending receipt, reassigned, SLA-risk, overdue, and escalated examples so every dashboard and queue state is demonstrable. Maintain a versioned seed-data manifest listing every fictional user, role, scope, station/region route, reference, document, expected queue count, and expected access outcome; it is the demonstration script and regression fixture.

Audits are append-only. Each entry captures actor or service identity, action, object type/reference, timestamp, source IP where available, result (`allowed` or `denied`), reason, and before/after values for changes. Exports and downloads record purpose and filters.

Before production, define retention schedules, lawful holds, redaction procedure, deletion authorization, encrypted backups, and restoration verification.

## 8. Analytics and Publication

Internal analytics provide 14-day and 30-day latency bands, regional comparisons, queue volume, dwell-time trends, and escalation flags. Public analytics are approved quarterly aggregates only, with small-cell suppression where ODPP policy requires it.

A scheduled, idempotent job computes snapshots with retries, failure alerts, and an auditable run record. Reporting data must not contain sealed Type A narratives or evidence. For the POC, notification, OCR, malware scanning, object storage, backup, and monitoring services are accessed through mockable adaptor interfaces with no production credentials.

### PDF reports and receipts

Generate server-side PDFs for case movement/custody history, scoped work queues, SLA and escalation reports, regional and national dashboard summaries, Type B complaint summaries, approved public quarterly aggregates, and the assisted-lodging or complaint receipt. PDFs must show report title, generated timestamp, scope/filters, generated-by identity, and a report reference. They are subject to the same permission checks, visibility rules, download audit events, and retention policy as on-screen data.

No report may include a sealed Type A narrative or evidence. Conduct reporting is limited to authorised aggregate counts and escalation metadata; detailed conduct records remain available only to authorised Internal Affairs users under conduct rules. Report templates must use ODPP-approved branding and be approved before production.

## 9. UX and Accessibility

Follow the prototype's two-door concept, staff queue orientation, document-folder case view, timeline emphasis, and restrained public disclosure. Support desktop and mobile. Public status labels must use plain language. The agreed accessibility standard must cover keyboard navigation, labelled controls, contrast, and error summaries.

Do not deploy demonstration accounts, passwords, mock records, or internal prototype navigation.

## 10. Delivery Sequence

1. Foundation: Django project; apps `accounts`, `cases`, `complaints`, `conduct`, `insight`, and `common`; custom user model; PostgreSQL databases; database router; object storage; environment settings.
2. Authorization: role enum, scope relationships, action matrix, service-level permission checks, audit system, and denied-access tests.
3. Case pipeline: assisted lodging terminal workflow, PIN/QR receipts, references, transition guards, append-only movements, asynchronous document/OCR queue, scoped staff views, reassignment, and three-station seed data.
4. Type B complaints: four-channel intake, public tracking, staff triage, automatic RSA-to-regional-to-HQ escalation, immutable directives, communication, ticket-style reassignment, SLA queues, and notifications.
5. Type A isolation: conduct models/database, sealed views, recusal checks, Internal Affairs-only narrative access, aggregate executive oversight, access auditing, and boundary tests.
6. Dashboards, reports, and pilot: role dashboards, analytics, generated PDFs, public aggregates, security review, backup/restore drill, training, paper-parallel pilot, and rollout review.

## 11. Minimum Acceptance Tests

- Public users cannot enumerate complaints or retrieve narrative, people, attachment, location, stage detail, or internal notes.
- A user outside scope is denied and an audit event is written.
- Registry users, an allocated RSA, a regional inspector, executive users, and external police liaison accounts each see only their permitted records and fields.
- A case transition or custody correction preserves history.
- A Type B complaint cannot close without communication proof.
- A Type A subject officer cannot discover or access their conduct file; the attempt is logged.
- The primary database cannot read or write sealed conduct narratives or evidence.
- Assisted-lodging PINs are hashed, QR codes disclose no sensitive information, receipt issuance is audited, and invalid public interactions cannot enumerate cases or complaints.
- Reassignment retains complete ownership and SLA history; risk, overdue, and escalation flags are correct after reassignment.
- Pilot dashboards show only each user's permitted scope, while the DPP and Deputy DPP see national operational data and aggregate conduct oversight without sealed narrative/evidence access.
- Controlled document uploads enforce type, size, malware scanning, visibility, audit, and download checks.
- OCR indexing keeps document search results, snippets, autocomplete, export, and downloads inside the user's object-level access scope.
- A process complaint opens with the RSA, auto-escalates after the configurable seven-working-day POC window, records a regional/HQ decision or `FileRecallOrder`, and preserves every transition in the ledger.
- Generated PDFs apply the same data scope and conduct restrictions as the interface and record their generation and download.
- PIN hashing, rate limits, uploads, transition guards, SLA calculations, and analytics snapshots are tested.
- Primary and conduct database restorations are tested separately.

## 12. Decisions Required Before Production

1. Confirm the station-to-region mapping, including whether Jinja Road belongs to the Nakawa ODPP region for this pilot.
2. Approve the role/action/scope matrix, including delegation and temporary coverage.
3. Approve evidence, retention, redaction, lawful-hold, and public-disclosure rules.
4. Confirm anonymous-complaint policy, lost-PIN recovery policy, and production notification channels.
5. Approve the Type A conduct state machine, sanitised handoff fields, reclassification process, and disposition policy.
6. Confirm production SLA targets, calendar, holiday source, escalation hierarchy, and communication templates; the POC uses a configurable seven-working-day RSA assumption.
7. Select production notification, OCR, malware-scanning, object-storage, backup, and monitoring providers.
8. Agree the public aggregate disclosure-control policy and accessibility target.
9. Approve the assisted-lodging terminal procedure, receipt format, QR locator payload, PIN recovery/reissue rules, and officer-identification disclosure policy.
10. Approve the official case-file document taxonomy, templates, metadata, file naming, and redaction rules with ODPP, Uganda Police, and Judiciary stakeholders.
11. Approve PDF report templates, report recipients, required branding, and any signing or watermarking requirements.
