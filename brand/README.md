# ODPP Brand System

This folder is the canonical brand source for the ODPP Case Pipeline and Complaints Console. Use it when creating or reviewing any Django template, stylesheet, PDF layout, email, exported report, or public-facing screen.

The visual source is [../brand.html](../brand.html). Do not introduce a different palette, font stack, status colour, or component style without updating this folder and receiving ODPP approval.

## Contents

| File | Purpose |
| --- | --- |
| `odpp.css` | Canonical colour tokens, typography, reusable application components, and accessibility defaults. |
| `django-base.html` | Starter shared Django template showing the correct stylesheet, font, icon, header, navigation, and content structure. |
| `implementation-guide.md` | Rules for applying the system consistently across staff, public, reporting, and document surfaces. |

## Quick Start for a Django Project

1. Copy `odpp.css` to the Django static path, normally `static/brand/odpp.css`.
2. Copy or adapt `django-base.html` into the shared `templates/base.html` template.
3. Add the project font links shown in the template. The supported typefaces are Cormorant Garamond 600 for display text and Nunito 400, 600, and 700 for all operational text.
4. Extend `base.html` for every page. Use the token variables and component classes instead of hard-coded colours, shadows, border radii, or font families.
5. Use the real ODPP crest from an approved static asset. Do not substitute a recreated crest or generic government icon.

## Non-Negotiable Tokens

| Token | Value | Use |
| --- | --- | --- |
| `--odpp-blue` | `#1E4699` | Identity hero, primary action, approved primary surfaces. |
| `--deep-blue` | `#12306B` | Utility strip, navigation, dark data surfaces. |
| `--blue-tint` | `#EAF0FA` | Subtle selected/secondary surfaces only. |
| `--crest-gold` | `#FFD200` | Small identity accent and focus signal. |
| `--crest-red` | `#D8232A` | Error, alert, and Type A conduct indicator. |
| `--ink` | `#1A1A1A` | Standard text. |

Use blue deliberately. The ODPP identity hero and utility strip are blue; normal application workspaces are white with precise blue, gold, and red signals. Avoid decorative gradients, oversized headings, rounded card-heavy layouts, and heavy shadows.

## Ownership and Change Control

The product owner approves brand changes. Any change to the crest, ODPP colours, public wording, document/report templates, or typography must be reviewed against `brand.html` and this source pack before it is released.
