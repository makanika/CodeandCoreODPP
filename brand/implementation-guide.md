# Applying the ODPP Brand System

## Page Hierarchy

Use the ODPP-blue `odpp-brandbar` only for the shared identity header. Use the Deep Blue `odpp-utility` for small institutional or signed-in context. Keep ordinary workspaces white. The application should feel like a precise case-management console, not a marketing site.

Use Cormorant Garamond 600 for page titles and case headings only. Use Nunito for all controls, tables, forms, reference numbers, status labels, body text, and reports. Do not use hero-scale headings inside dashboard panels, queues, or case folders.

## Staff Workspaces

- Dashboards: dense, scannable counts and tables; show scope and date range close to the title.
- Queues: use `odpp-table`; put SLA status and current custodian in dedicated columns.
- Case folders: stable case reference at the top, then current custody, timeline, permitted actions, documents, and audit history.
- Complaints: make Type A `odpp-badge--conduct` visibly distinct, but never reveal a Type A record to an excluded user.
- Forms: use `odpp-field`; group related fields with fieldsets and legends; show validation immediately below the associated control.

## Public Screens

Public complaint and tracking pages are intentionally sparse. Do not show staff navigation, case-pipeline details, officer names, file locations, attachments, or internal notes. Use the ODPP identity header at the compact size shown in `django-base.html` and clear, respectful plain-language status text.

## Status Colours

| Status | Class | Meaning |
| --- | --- | --- |
| Sanctioned | `odpp-badge--sanctioned` | Prosecutorial approval/action. |
| DFI issued | `odpp-badge--dfi` | Further investigation directed. |
| Closed / nolle | `odpp-badge--closed` | Case or inquiry is closed. |
| SLA breach | `odpp-badge--breach` | Needs visible operational escalation. |
| Under perusal | `odpp-badge--perusal` | Active ODPP review. |
| Conduct | `odpp-badge--conduct` | Restricted Type A handling only. |

Colour supports text; it cannot be the only way a person learns a status. Include a clear text label and, where useful, an icon or short explanatory phrase.

## Reports, PDFs, and Emails

Use the same token values and typography in PDF and email templates. Reports are primarily white with a compact ODPP-blue masthead, a Deep Blue metadata strip, and clear tables. Show report title, generated timestamp, filters/scope, and report reference. PDF generation must apply the same access filtering as the web view.

## Accessibility and Quality Checks

Before merging a screen, verify:

- keyboard focus is visible using the gold focus ring;
- every input has a visible label and errors are linked to it;
- no status relies on colour alone;
- text remains readable at 200% zoom and narrow mobile widths;
- controls are at least 34px high and text does not clip;
- page titles, tables, status badges, and controls use only tokens from `odpp.css`;
- Type A conduct material is absent, not merely hidden, from views and exports without access.

## Prohibited Patterns

Do not introduce purple, gradients, oversized hero treatments, round card-heavy layouts, blurred decorative backgrounds, default browser fonts, unapproved crest artwork, or hard-coded colour values. Do not make a public tracker look like a public case-search portal.
