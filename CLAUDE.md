# Mots en commun: instructions for Claude Code

Mots en commun is a free, self-hosted Django site where French learners and native speakers record and look up French expressions that don't mean what their words suggest.

**The spec is `docs/prd.md`. It is the source of truth.** Read it in full before starting any milestone. If the PRD is unclear, contradicts itself or seems wrong, stop and ask the owner. Don't guess, and don't quietly build something different. Suggest a change to the PRD instead.

## Scope

- Build **phase 1 only** ("Le site de base"), and the phase 1 parts of the Security and Deploying sections.
- Phase 2+ features (invitations, `Signalement`, public contribution forms, illustrations, recordings) are **not** built yet. The models reserved for later are not created yet either.
- In phase 1, reviewer accounts are created by hand by the owner in the admin.

## Language: French first

- **Identifiers** are in French, in ASCII without accents: models, fields, variables, functions, URLs, management commands, templates, CSS classes. Examples: `Entree`, `sens_b1`, `importer_donnees_initiales`, `/fr/expressions/`. Django and Python reserved names stay as they are.
- **Comments, docstrings, scripts and their output, and `CONTRIBUTING.md`** are in French.
- **Interface text** is written in French and marked for translation (`gettext`, `{% translate %}`, `{% blocktranslate %}`). No English text is built into the interface.
- **Commit messages and pull request descriptions** are preferably in French.
- **`README.md`** is in French, and `README.en.md` is its English translation. No other README translations are created; the PRD explains how contributors add them.

## How to work

- Work through the milestones below **in order, one at a time**.
- For each milestone, plan first: list what you'll build and which acceptance criteria from the PRD it covers, then build it.
- Work on a branch, make small focused commits, and open a pull request at the end of each milestone. **Never push to `main`.**
- Each PR description lists the acceptance criteria it satisfies and how each is tested. Then **stop and wait for the owner's review** before starting the next milestone.
- Every acceptance criterion that code can check becomes a test (pytest-django). Run the full test suite before every commit. A milestone isn't finished while any test fails.
- Use `uv` for everything: `uv add`, `uv run pytest`, `uv run python manage.py …`. Python and all dependencies are pinned in the lock file.

## Hard rules

- **Secrets:** never write, print, log or commit one. Settings come from environment variables; the repository holds only `deploiement/env.exemple` with placeholder values.
- **Privacy:**
  - Public pages set no cookies and make no requests to any other site. No CDN, no external fonts, no analytics.
  - Nothing stores visitor IP addresses, and nothing writes access logs.
- **JavaScript:** none on public pages, except the *Confort de lecture* switch. Every page must work with JavaScript off.
- **Contributor text is never HTML:** never use `|safe`, `mark_safe` or `format_html` on contributor-written fields.
- **Only reviewed content is public:** anything that isn't `relu` or `valide` must not appear anywhere public, and its URL returns 404 to visitors.
- **Dependencies:** add one only when it's clearly needed, and say why in the PR. Pin GitHub Actions to full commit SHAs.
- **The real server:** write the deployment scripts and test them locally (a throwaway VM or container). **Never** connect to, deploy to, or change the real server, DNS, Scaleway or any account. The owner runs those steps.
- **Seed data:** the archive in `donnees/import/donnees-initiales.zip` was drafted by AI and may contain errors. It is imported with `statut = brouillon` and is never treated as reviewed. Keep the 82 example sentences marked as placeholders.

## Milestones (phase 1)

1. **Socle (foundation):**
   - the `motsencommun` project and `lexique` app, with settings from environment variables
   - pytest-django, and GitHub Actions running the tests and `pip-audit`
   - Dependabot config
   - `LICENCE-DONNEES`, `LICENCE-CODE`, `README.md`, `README.en.md`, `CONTRIBUTING.md`, `SECURITY.md`
2. **Modèle de données (data model):**
   - the phase 1 models, `vocabulaire.py`, history on every model, and the `statut` rules and validation
   - the admin, with a reviewer group that has reviewing permissions only
   - required TOTP for superusers, Argon2 with 16-character passwords, login throttling and session settings
3. **Import:** `importer_donnees_initiales`, following the PRD's mapping table, with tests for the mapping.
4. **Recherche et alphabets (search and alphabets):** NFC normalisation, the precomputed search field, French-only accent folding, per-language sorting, with tests in Ukrainian and Polish.
5. **Site public (public site):**
   - pages and URLs with language prefixes, and the display rules
   - the *Mon niveau* level display and its fallback
   - reviewers' preview of drafts while logged in
   - print styles
6. **Apparence (look and feel):** the single CSS file, self-hosted Literata, dark mode, and the *Confort de lecture* switch with lazily loaded OpenDyslexic.
7. **Visibilité et intégration (findability and embedding):** security headers, `sitemap.xml`, `robots.txt`, Open Graph images, embed pages and `security.txt`.
8. **Téléchargements (downloads):** `exporter`, the data dictionary, and monthly snapshots.
9. **Déploiement (deployment):** everything in `deploiement/`:
   - `installer-serveur.sh` (including WireGuard), `deployer.sh`, `sauvegarder.sh` and `restaurer.sh --a-la-date`
   - the Caddyfile, systemd units and timers, and the alerts
   - `INCIDENT.md`
   - a README explaining each step the owner runs
10. **Vérification (verification):** go through every phase 1 acceptance criterion in the PRD. Report each one as met, met by a test (name it), or needing the owner (say what they need to do).
