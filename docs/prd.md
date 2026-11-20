# Mots en commun — PRD (v1)

Nov 18, 2026 · @Colin

## Summary

**Mots en commun** is a free, self-hosted website where French learners and native speakers record and look up the French expressions that don't mean what their words suggest. It covers expressions like *être en train de*, *en vouloir à quelqu'un* and *poser un lapin*. Each entry has a plain explanation, its level, the traps it sets, and simple example sentences.

*Les expressions françaises, expliquées par ceux qui les apprennent et ceux qui les parlent.*

The site is useful from the first page to learners and teachers browsing lists. Everything is built in French first: tables, fields, URLs and interface. Other languages are a separate layer that contributors add. The whole list can be downloaded as structured data, so developers and AI tools can build on it.

The project is community-run and self-funded. There's no tracking and no advertising, and it isn't a commercial venture.

This document is the build spec. Phase 1 is what Claude Code builds first; later phases are described so the data model leaves room for them.

## Why it exists and who it's for

Learners keep stumbling on phrases where every word is familiar but the meaning isn't. *Il m'en veut* has nothing to do with wanting. *C'est pas terrible* means "it's not great". *Je suis en train de* has nothing to do with trains. Explanations of these are scattered across blogs and textbooks. None of them is one shared, growing, searchable place, built by the people who learn and speak the language.

| Who | What they come for |
| --- | --- |
| **Learner** | Look up a phrase they just met; browse expressions at their level; see real example sentences |
| **Teacher** | Find and print a list of expressions by level, type or topic for a lesson |
| **Contributor** (phase 2) | Add an expression they had to learn the hard way, or a native speaker's explanation of one |
| **Translator** (phase 2) | Make the explanations available in their language: Polish, Ukrainian, English, and others |
| **Reviewer** (phase 2) | Check that entries are accurate and natural before they're published |
| **Developer or AI builder** | Download the whole list as structured data to build learning tools |
| **Owner** (phase 1) | Add and edit every entry through the admin, alone, until contributors join |

## Goals, non-goals and principles

**Goals**

- A clear, fast site for looking up and browsing French expressions and their traps.
- A data model that grows from one author to many contributors, then to pictures and recordings, without being redesigned.
- A full history of every change, with credit to whoever made it.
- Free downloads of the whole list.

**Non-goals**

- A full dictionary. Only expressions and words that trip learners up belong here.
- Courses, exercises or gamification.
- Accounts for readers. Reading is anonymous.
- Commercial features, advertising, tracking or analytics.
- Success metrics. This is a community project.

**Principles**

1. **French first.** Everything the project defines is named in French: models, tables, fields, URLs, codes and interface. Only Django's own reserved words stay in English. Identifiers use ASCII without accents; accents belong in content and labels.
2. **Other languages are contributed, not built in.** The core holds French only. Translations are a separate layer, each with its own contributor and review.
3. **Every alphabet works.** Latin, Cyrillic and right-to-left scripts work from day one.
4. **Private by design.** No cookies on public pages, no third-party requests, no tracking. JavaScript is welcome where it makes the site better for readers, never to track them.
5. **Simple and fast.** Server-rendered HTML, one small stylesheet, and pages that work without JavaScript.
6. **Nothing is lost.** Every change is recorded with who made it and when, and kept forever.

## User stories by phase

| # | As a… | I want to… | Phase |
| --- | --- | --- | --- |
| H1 | Learner | search for a phrase, ignoring accents and capitals (*etre en train* finds *Être en train de*) | 1 |
| H2 | Learner | read what an expression means, what it literally says, and why it's confusing | 1 |
| H3 | Learner | browse expressions at my level, or of one type such as false friends | 1 |
| H4 | Learner | see simple example sentences, with the expression highlighted | 1 |
| H5 | Teacher | print or share a filtered list, e.g. "B1 idioms about emotions" | 1 |
| H6 | Learner | read the interface and explanations in my language, when a translation exists | 1 (interface), 2 (content) |
| H7 | Developer | download the whole list as JSON or CSV, with a data dictionary | 1 |
| H8 | Owner | add and edit expressions, traps and examples in a simple admin, with full history | 1 |
| H9 | Contributor | create an account, propose a new expression or example, or report an error and suggest a fix on an existing entry | 2 |
| H10 | Reviewer | approve or send back proposals, never my own | 2 |
| H11 | Translator | translate explanations and interface text into my language | 2 |
| H12 | Learner | see a picture that helps me remember an expression | 3 |
| H13 | Native speaker | record myself reading an example sentence | 4 |
| H14 | Learner | hear example sentences read by real people | 4 |

## Phases

| Phase | What it adds | Gate to open the next phase |
|---|---|---|
| **1 · Le site de base** (build now) | Browse, search, filter; entry pages, printing; downloads, admin; 73 AI-drafted test entries for trying it out, none of them on the live site | **Open to others:** native reviewers found, data model settled |
| **2 · Contributeurs** | Accounts and roles; proposals and review; translations (pl, uk…); public forms | **Image rules:** picture rights policy agreed and published |
| **3 · Illustrations** | Pictures on entries; credit and licence; alt text required | **Consent ready:** voice licence agreed, storage and moderation in place |
| **4 · Enregistrements** | Read-aloud recordings; consent per file; moderation | — |

The phases have no dates. Each opens when its gate is met, at whatever pace the community sets.

## Phase 1 site: pages, URLs and behaviour

Every public URL starts with a language prefix that sets the interface language: `/fr/` by default, `/en/`, `/pl/`, `/uk/` as translations exist. The rest of the path stays in French whatever the language. Switching language is a plain link to the same page under another prefix, with no cookie. The language comes only from the prefix, never from the browser's settings or a cookie: `/` leads to `/fr/`, and the admin, which has no prefix, stays in French (decided 20 November 2026).

| Page | URL | What it shows |
| --- | --- | --- |
| Accueil | `/fr/` | Search box, one-line introduction, browse by level, type and theme, recently added entries |
| Liste | `/fr/expressions/` | All entries, alphabetical by `vedette`, 50 per page. Filters in the query string, so any filtered list is a shareable link: `?niveau=B1&type=faux_ami&theme=emotions&registre=familier` |
| Raccourcis | `/fr/niveau/b1/`, `/fr/type/faux-ami/`, `/fr/theme/emotions/` | The same list, pre-filtered, with a heading |
| Fiche | `/fr/expressions/poser-un-lapin/` | One entry: the full layout is below |
| Recherche | `/fr/recherche/?q=…` | Results across `vedette`, `formes`, `sens` and translations in the current language. Accents and capitals are ignored. Every word of the query must appear, in any order (decided 20 November 2026). Exact matches of a `vedette` or form come first, then those that contain the query |
| Télécharger | `/fr/telecharger/` | Download links, data dictionary, licence |
| À propos | `/fr/a-propos/` | The project, contributor credits, licence, privacy statement ("this site sets no cookies") |
| Admin | A non-obvious path set in configuration | Django admin, for the owner in phase 1 |

**An entry page (fiche) shows, in order:**

1. **The header:** `vedette`, then `nature`, `niveau`, `registre` and `regions` as small labels.
2. **The meaning:** the `sens_…` version that matches the reader's level (see the display rules below) and, for idioms, `sens_litteral`.
3. **Its traps (pièges):** each with its type label, gravité (severity) and explanation. Where there is an `incorrect` / `correct` pair, it's shown as ✗ / ✓.
4. **Examples:** sentences with the expression highlighted using `<mark>`, plus any translation in the reader's language.
5. **Related entries:** "voir aussi" and "à ne pas confondre avec" links.
6. **A footer line:** who added it, when it was last changed, and its review status.
7. **A *Signaler une erreur* button (phase 2, logged-in contributors only):** it opens a short built-in form with two fields: what's wrong, and, optionally, the proposed correction. There's no email field, because the account already says who sent it. The report is saved as a `Signalement` attached to the entry and appears in the admin next to it. Readers who aren't logged in see a link to log in or request an account instead. In phase 1 only the owner can log in, so the button appears once contributor accounts open.

**Display rules**

- **Only reviewed content is public.** Entries, traps and examples that aren't `relu` or `valide` appear nowhere on the public site: not in lists, search, themes, links between entries, embeds, the sitemap or downloads. Their URLs return 404 to visitors. When logged in, the owner and reviewers see them on the normal entry page with a *Pas encore relu* banner, so they review exactly what readers will see. A reviewed entry shows only its reviewed traps and examples.
- **Missing translations fall back to French.** When there's no approved translation in the interface language, the French text is shown, marked with `lang="fr"`. The French meaning, explanations and sentences are always shown, since they're what the reader is learning; an approved translation in the interface language appears beside them, with its own `lang`.
- **Lists print cleanly.** A print stylesheet removes navigation and fits entries on paper, so a teacher prints straight from the browser.
- **Every page works without JavaScript.**
- **Teachers can embed entries.** Each entry has an embed page (`/fr/expressions/poser-un-lapin/integrer/`): the entry alone, with no navigation, plus a small link back to the full page. Only these pages may be shown inside other sites, such as a course site or Moodle. The entry page offers a ready-to-copy `<iframe>` code.
- **Explanations follow the reader's level.** A *Mon niveau* selector (A1–C2) sits beside the search box. Each meaning and trap explanation shows the highest version written at or below the reader's level, and the lowest available version if none is. When the reader hasn't chosen a level, the entry's own level is used. The choice is a `?mon_niveau=A2` parameter in the URL, so it works without JavaScript and can be shared. Links carry it from page to page. It only chooses which version is shown and never filters a list; the list's level filter is the separate `?niveau=B1` (decided 20 November 2026). With JavaScript it's also remembered in `localStorage`, like the reading-comfort switch. A small note says which level's version is shown, with links to the others.

## Look and feel

Plain and calm, like a well-set dictionary page: the words are the design.

- **Type:** **Literata**, one self-hosted variable font for everything, under the SIL Open Font License, covering Latin, Latin Extended and Cyrillic. It's served as WOFF2 from our own server, cut down to just those characters, with `font-display: swap` so text appears at once in a fallback font while it loads. Scripts it doesn't cover (Arabic, Hebrew…) fall back to system fonts. Body text at least 17 px, lines no longer than about 70 characters, line height 1.5.
- **Reading comfort mode (*Confort de lecture*):** a switch at the top of every page for readers with dyslexia, or anyone who finds dense text hard. When it's on:
  - the font becomes **OpenDyslexic** (SIL Open Font License, covers Latin and Cyrillic)
  - text is larger
  - letter spacing and word spacing increase *together*: more space between letters alone slows reading
  - line height increases
  - italics and justified text are turned off
  - the background is a soft cream, with an equivalent in dark mode

  Research finds that the spacing does most of the work, not the letter shapes, which is why the mode changes both. The OpenDyslexic file downloads only when the mode is first switched on, so nobody else pays for it. The choice is remembered in the browser's `localStorage`: it's never sent to the server and it isn't a cookie. The switch needs JavaScript; without it, the switch is simply hidden.
- **Spacing must never break the layout.** Pages must still work when readers apply their own spacing through browser extensions (WCAG 2.2 success criterion 1.4.12, Text Spacing).
- **Colour:** near-black text on off-white, and one deep blue accent colour for links and level labels, adjusted to pass contrast checks in both light and dark mode. Severity is shown with words and a shape as well as colour, never by colour alone.
- **Highlights:** `<mark>` in a soft colour that stays readable when printed in black and white.
- **Dark mode:** follows the device setting through `prefers-color-scheme`, with no toggle and no cookie.
- **Layout:** one column, designed for phones first, with the search box at the top of every page.
- **Never:** carousels, pop-ups, banners, icon fonts or decorative animation.
- **Favicon:** one small SVG file.
- **Logo:** the name *Mots en commun* set in the site's font, with no image. The favicon is the letters *Mc* in deep blue.

## Data model

The Django project is `motsencommun` and holds one app, `lexique`. Every model gets automatic history through django-simple-history. Every model except the vocabulary-like ones carries `cree_le`, `modifie_le`, `ajoute_par` and `statut`: entries, traps, examples and their translations. They also carry `texte_modifie_le`, the last time their text changed, which decides which reviews still count. Every model that the seed import fills also has a read-only `genere_par_ia` flag (see the seed data section).

### `Entree`: a word or expression (table `lexique_entree`)

| Field | Type | Notes |
| --- | --- | --- |
| `slug` | slug, unique | ASCII, from `vedette`: `poser-un-lapin`. Permanent |
| `vedette` | text | Citation form: *poser un lapin à qqn* |
| `precision` | text, optional | Tells apart two entries with the same `vedette`: *avant le nom* |
| `type_entree` | code | `mot`, `expression`, `construction` |
| `nature` | code | Part of speech: `nom`, `verbe`, `locution_verbale`… |
| `genre` | code, optional | `masculin`, `feminin`, `epicene`, `pluriel_seulement` |
| `api` | text, optional | Pronunciation in the International Phonetic Alphabet |
| `sens_a1` … `sens_c2` | six texts, each optional | The meaning, explained in French at each level, one to three sentences each. Fill in the entry's own level first. At least one level must be filled in before review |
| `sens_litteral` | text, optional | Word-for-word reading, for idioms |
| `niveau` | code | A1–C2 |
| `registre` | code | `soutenu`, `courant`, `familier`, `tres_familier`, `vulgaire`, `argot` |
| `frequence` | code | `tres_courante`, `courante`, `peu_courante`, `rare` |
| `regions` | many codes | Empty means everywhere |
| `themes` | many-to-many to `Theme` |  |
| `formes` | list of text | Spellings to search for: *j'en ai marre, t'en as marre…* |
| `liens` | through `LienEntree` | `type_lien` (`voir_aussi`, `contraire`, `a_ne_pas_confondre`, `variante`) and the target entry |
| `cree_le`, `modifie_le`, `ajoute_par`, `statut` |  | Common fields |

### `Piege`: why an entry is confusing (table `lexique_piege`)

| Field | Type | Notes |
| --- | --- | --- |
| `entree` | foreign key | One entry has one or more traps |
| `type_piege` | code | One of the 18 types in the vocabularies section |
| `concerne` | many codes | `comprehension`, `production` |
| `gravite` | code | `faible`, `moyenne`, `elevee` |
| `langue_apprenant` | language code, optional | Set when the trap depends on the learner's language (`en` for *actuellement* ≠ "actually"); empty when it's universal |
| `declencheur` | text, optional | The learner-language word that causes it ("actually") |
| `explication_a1` … `explication_c2` | six texts, each optional | Why it's confusing, explained in French at each level. At least one level before review |
| `incorrect`, `correct` | text, optional | A minimal pair |
| common fields |  |  |

### `Exemple`: an example sentence (table `lexique_exemple`)

One sentence is one `Exemple`, even when it illustrates several entries (decided 19 November 2026): it is reviewed, translated and, in phase 4, recorded once.

| Field | Type | Notes |
| --- | --- | --- |
| `phrase` | text | Original French |
| `niveau` | code | Level of the whole sentence |
| `entrees` | through `ExempleEntree` | The entries the sentence illustrates, at least one before review |
| common fields |  |  |

### `ExempleEntree`: an example on an entry (table `lexique_exempleentree`)

| Field | Type | Notes |
| --- | --- | --- |
| `exemple`, `entree` | foreign keys | One row per sentence and entry |
| `surlignage` | text | Exact words in `phrase` to highlight for this entry. Validated on save |
| `ordre` | integer | Display order on the entry page |

### Supporting tables

- **`Theme`:** `slug`, `nom` (in French). Translations go in `ThemeTraduction`.
- **`Contributeur`:** Django's `User` plus a profile with `nom_affiche` (the name credited publicly, in any script), `langues` (the languages they speak), `licence_acceptee_le` (when they accepted the data licence), `invitation` (the invitation used to sign up, if any; added in phase 2 with the `Invitation` table) and `relit_langues` (for reviewers: the content they may review, `fr` and/or translation languages, set only by the owner).
- **Translations:** `EntreeTraduction`, `PiegeTraduction`, `ExempleTraduction` and `ThemeTraduction`, described in the translations section.
- **`Signalement` (phase 2):** an error report on an entry. Fields:
  - `entree`
  - `auteur` (the logged-in contributor)
  - `message` (what's wrong)
  - `correction_proposee` (optional)
  - `statut`: `nouveau`, `traite` or `rejete`
  - `cree_le`, `traite_par`, `traite_le`

  A correction that's accepted becomes an ordinary edit to the entry, credited to the reporter and recorded in the history.
- **`Invitation` (phase 2):** a signup invitation. Fields: `code_hache`, `role` (`contributeur` or `relecteur`), `relit_langues`, `note`, `creee_par`, `creee_le`, `expire_le`, `utilisations_max` (always 1 for reviewers), `revoquee_le`. The accounts that used it are found through `Contributeur.invitation`. History is kept like everything else.

### Reserved for later phases

These tables are named now but not built in phase 1:

- **`Illustration` (phase 3):** `entree`, `image`, `texte_alternatif`, `credit`, `licence`, common fields.
- **`Enregistrement` (phase 4):** `exemple`, `fichier_audio`, `locuteur`, `region_accent`, `consentement_le`, `retire_le`, `licence`, common fields. Decided 19 November 2026: recordings are made on the site itself, not through Lingua Libre (whose CC BY-SA licence, Wikimedia Commons hosting and uncertain funding don't fit). A logged-in contributor records in the browser on the editing page. Audio is stored on our server and licensed CC BY 4.0, accepted at the moment of recording. A voice is personal data, so a speaker can withdraw a recording at any time (`retire_le`), and it then leaves the site and future downloads. A recording appears only once reviewed. Formats, size limits and the review steps are settled at the phase 4 gate.

The diagram below shows how the tables connect.

Everything hangs off an `Entree`; translations sit beside it.

```
Theme (slug, nom) ──themes── Entree (vedette, niveau, sens_a1 … sens_c2, formes, statut, ajoute_par)
                                │
        ┌───────────────────────┼─────────────────────────┬──────────────────────────────┐
        │ 1..n                  │ n..n                    │ 0..n                         │ 0..n
      Piege            ExempleEntree               LienEntree                [Illustration · phase 3]
 (type_piege, gravite,  (surlignage, ordre)       (type_lien, cible:         (image, texte_alternatif,
  concerne,                    │                   voir_aussi, contraire…)     credit, licence)
  langue_apprenant,         Exemple (phrase, niveau)
  explication_…)               │ 0..n
                          [Enregistrement · phase 4]
                          (fichier_audio, locuteur, consentement_le, licence)

Traductions: EntreeTraduction, PiegeTraduction, ExempleTraduction, ThemeTraduction · one per langue
Historique:  django-simple-history on every table · Relecture records each review, never by an author or editor
```

Boxes in [brackets] are reserved for later phases.

Reviews live in a `Relecture` table: the reviewed record (`contenu`), `relecteur`, `decision` (`approuve` or `refuse`), `commentaire`, `date`. A review is never changed once saved.

## Vocabularies

Codes are ASCII and stored in the database. Each has a French label with accents, which is translatable like any other interface text. In Django these are `TextChoices` classes in `lexique/vocabulaire.py`.

| Vocabulary | Codes |
| --- | --- |
| `niveau` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` |
| `type_entree` | `mot`, `expression`, `construction` |
| `nature` | `nom`, `verbe`, `adjectif`, `adverbe`, `preposition`, `conjonction`, `pronom`, `determinant`, `numeral`, `interjection`, `locution_verbale`, `locution_nominale`, `locution_adjectivale`, `locution_adverbiale`, `locution_prepositionnelle`, `locution_conjonctive`, `phrase` |
| `genre` | `masculin`, `feminin`, `epicene`, `pluriel_seulement` |
| `registre` | `soutenu`, `courant`, `familier`, `tres_familier`, `vulgaire`, `argot` |
| `frequence` | `tres_courante`, `courante`, `peu_courante`, `rare` |
| `region` | `FR`, `BE`, `CH`, `CA_QC`, `LU`, `AF` |
| `concerne` | `comprehension`, `production` |
| `gravite` | `faible`, `moyenne`, `elevee` |
| `type_lien` | `voir_aussi`, `contraire`, `a_ne_pas_confondre`, `variante` |
| `statut` | `brouillon`, `en_relecture`, `relu`, `valide`, `refuse`, `retire` |
| `langue` | ISO 639-1 codes: `fr`, `en`, `pl`, `uk`, `es`, `de`… (`uk` is Ukrainian; `ua` is a country code, not a language) |

### `type_piege`: the 18 trap types

| Code | Label | What goes wrong | Example |
| --- | --- | --- | --- |
| `sens_figure` | Sens figuré | The meaning can't be built from the words | *poser un lapin* |
| `faux_ami` | Faux ami | Looks like a word in the learner's language but means something else | *actuellement* (for English speakers) |
| `faux_ami_partiel` | Faux ami partiel | Partly overlaps, but the main meaning differs | *réaliser* |
| `connotation` | Connotation | Neutral in the learner's language, loaded in French | *excité* |
| `calque` | Calque | A word-for-word translation natives don't say | *je suis chaud* for "I'm hot" |
| `construction_inversee` | Construction inversée | Subject and object swap places | *tu me manques* |
| `sens_selon_position` | Sens selon la position | Meaning changes before or after the noun | *un ancien élève* / *une maison ancienne* |
| `sens_selon_genre` | Sens selon le genre | Gender changes the meaning | *le tour* / *la tour* |
| `polarite` | Polarité | Negation or understatement flips the expected meaning | *pas mal*, *pas terrible* |
| `prononciation` | Prononciation | Spelling misleads the pronunciation | *plus*, *fils*, *héros* |
| `mode_impose` | Mode imposé | Forces the subjunctive, or forbids it | *bien que* |
| `preposition` | Préposition | Different preposition from the learner's language | *tomber amoureux de* |
| `forme_figee` | Forme figée | A fixed part that learners drop or change | *j'en ai marre* |
| `confusion_possible` | Confusion possible | Easily confused with another French expression | *en fait* / *en effet* |
| `forme_irreguliere` | Forme irrégulière | Breaks the usual rules of form or agreement | *gens* |
| `registre` | Registre | Fine with friends, wrong at work, or the reverse | *boulot*, *kiffer* |
| `regional` | Régional | Different meaning, or unknown, in another region | *dîner* in Québec |
| `pragmatique` | Pragmatique | A conversational role with no direct equivalent | *quand même*, *du coup* |

Traps of type `faux_ami`, `faux_ami_partiel`, `calque`, `connotation` and `preposition` normally depend on the learner's language, so `langue_apprenant` should be set. The others are usually universal.

## Translations

The core is French and complete on its own. Every other language is an optional layer, added by contributors and reviewed like everything else.

**Content translations** are one table per translated model, each holding only the text fields:

| Table | Fields translated | Extra fields |
| --- | --- | --- |
| `EntreeTraduction` | `sens`, `sens_litteral` (one version, not one per level: someone reading in their own language doesn't need simplified French) | `entree`, `langue`, common fields |
| `PiegeTraduction` | `explication` | `piege`, `langue`, common fields |
| `ExempleTraduction` | `traduction` (the sentence in that language) | `exemple`, `langue`, common fields |
| `ThemeTraduction` | `nom` | `theme`, `langue` |

There is one row per record and language, enforced by a uniqueness constraint on (record, `langue`). The site shows a translation only once its `statut` is `relu` or `valide`, and otherwise falls back to French. `ThemeTraduction` is the exception: theme names are vocabulary managed by the owner, without a `statut`.

**Interface text** is written in French in the templates and code, using Django's translation functions (`gettext`, `{% translate %}`, `{% blocktranslate count %}` for plurals). Other languages live in standard `.po` files under `locale/`. In phase 1 the owner can add English interface strings. From phase 2, contributors can translate them too. A self-hosted Weblate is one option for this, if editing `.po` files by hand becomes a barrier.

**Vocabulary labels** (levels, trap types, registers…) are interface text, so they're translated through the same `.po` files.

**What is *not* a translation:** `langue_apprenant` on a trap. A false friend for English speakers is a separate fact from a false friend for Polish speakers, so each gets its own `Piege` row. Translating a trap's explanation into Polish doesn't make it a Polish speaker's trap.

## Every alphabet

Ukrainian and Polish contributors are expected from the start, and right-to-left languages must be possible later. These are requirements, not nice-to-haves.

1. **UTF-8 everywhere:** database, files, HTTP responses and downloads.
2. **Normalise every saved text field to Unicode NFC**, in the model's `clean()` and `save()`. Also convert typographic apostrophes (’) to straight ones (') in `formes`, `surlignage` and the example's `phrase` (decided 20 November 2026), so searches and highlights match character for character.
3. **Search through a precomputed field, not the database's case handling.** SQLite only treats upper and lower case as equal for unaccented ASCII letters, so `É`/`é` and `К`/`к` wouldn't match. `Entree` (`vedette`, `formes`, `sens_…`) and `EntreeTraduction` (`sens`, in its own language) store a `recherche` field, built in Python on save by `lexique/recherche.py`:
   - Python `casefold()`, with every way of typing an apostrophe treated as the same.
   - For French text only, strip accents and ligatures (*être* → *etre*, *cœur* → *coeur*), and only from Latin letters.
   - Never strip marks from other languages. Removing the breve turns Ukrainian *й* into a different letter, *и*. Polish *ł* must stay *ł*.
4. **Sort by each language's alphabet, with PyICU.** Polish *ł* sorts after *l*, not after *z*. Entries store their ICU sort key (`cle_de_tri`: the `vedette`, then the `precision`), so lists are sorted and paginated by the database. Shorter lists, such as translated theme names, are sorted in Python with the same collation.

The `recherche` and `cle_de_tri` fields are derived: they can't be edited, aren't kept in the history, and never count as a change of text, so they never send content back to review. `python manage.py reconstruire_recherche` recomputes them, for example after the rules change or the server's ICU is upgraded (sort keys depend on the ICU version).
5. **Mark the language and direction of text.** Every block of translated text carries `lang` and `dir` attributes, and the page's `<html lang dir>` follows the interface language. Use CSS logical properties (`margin-inline-start`, not `margin-left`) so right-to-left needs no second stylesheet.
6. **Fonts:** the system font stack, which covers Latin, Latin Extended and Cyrillic on every common device. Any web font must be self-hosted and include those ranges. No Google Fonts.
7. **Plurals:** Polish and Ukrainian have three or more plural forms. Interface strings with numbers must use Django's plural support, never strings glued together by hand.
8. **Names:** contributor display names accept any script. Only slugs and codes are ASCII.
9. **CSV:** written as UTF-8 with a byte-order mark, so spreadsheet programs display Cyrillic and Polish letters correctly.
10. **Tests:** the test suite includes fixtures in Ukrainian and Polish that cover search, sorting, highlighting and export.

## Privacy, performance and accessibility

**Privacy**

- **No cookies on public pages.** Public views must not set a session or CSRF cookie: no `{% csrf_token %}` on public templates, and no session access. Cookies appear only in the admin and, from phase 2, for logged-in contributors.
- **No third-party requests at all:** no fonts, scripts, analytics, maps or embeds from other servers.
- **JavaScript only for the reader's benefit** (decided 19 November 2026). Scripts may make the site better for readers, such as the reading-comfort switch or remembering *Mon niveau*, but never track them: no analytics, fingerprinting or beacons, and nothing that records or profiles what a reader does. Scripts are files on our own server, never inline, and every page still works without them.
- **Server logs only.** Keep them short (e.g. 14 days), and never send them to a third-party service.
- **Data collected from contributors (phase 2):** an email address for login, plus the display name they choose. Nothing else. The À propos page explains this in plain words.
- **Strict security headers, set by Caddy:**
  - `Content-Security-Policy: default-src 'self'`, which also makes every browser enforce the no-third-party rule. Scripts and styles are files, never inline.
  - `frame-ancestors 'none'`, so no other site can frame the pages. The one exception is the embed pages, which allow framing anywhere (see the entry page section).
  - `Strict-Transport-Security: max-age=31536000` (one year), so browsers always use HTTPS. Not submitted to the browsers' preload list for now, because it's hard to undo.
  - `Referrer-Policy: no-referrer` and `X-Content-Type-Options: nosniff`.
  - A `Permissions-Policy` that turns off camera, microphone and location until phase 4 needs the microphone.
- **Reporting security problems:** `/.well-known/security.txt` and a `SECURITY.md` in the repository both point to the GitHub repository's *private* vulnerability reporting (`/security/advisories/new`), not to public issues. That way a flaw isn't published before it's fixed. Ordinary bugs go to public GitHub issues.

**Performance targets** (design budgets, not tracked metrics)

- An entry page is under 30 KB of HTML and CSS combined, with no JavaScript required.
- Pages render on the server in under 100 ms on the production machine, with full-page caching for anonymous visitors.
- One stylesheet. No CSS framework.
- Images (phase 3) are served as compressed WebP or AVIF, with width and height set, and loaded lazily.

**Accessibility**

- Target WCAG 2.2 level AA.
- Semantic HTML: `<mark>` for highlights, `<dl>` for an entry's properties, real headings and labelled form fields.
- Text contrast at least 4.5:1, readable at 200% zoom, and full keyboard navigation.
- Every image has `texte_alternatif` (alt text). Every recording (phase 4) has its written sentence next to it.

## Findability

Learners and teachers mostly arrive from a search engine, so every page should be easy to find and share, without any tracking.

- **Page titles:** `poser un lapin à qqn — Mots en commun`. The meta description is the entry's `sens`.
- **Language versions:** an entry page declares an `hreflang` alternate only for languages in which that entry has a reviewed translation. In other languages, the page's canonical URL points to the French version, so search engines don't see near-identical copies.
- **Unreviewed entries are never indexed.** Visitors get a 404 for them, and the pages reviewers see while logged in carry `<meta name="robots" content="noindex">`. They never appear in the sitemap.
- **`sitemap.xml` and `robots.txt`**, both generated by Django. The sitemap lists reviewed entries only. `robots.txt` welcomes search engines, but asks known AI-training crawlers (GPTBot, ClaudeBot, Google-Extended, CCBot and similar, kept as a list in settings) not to crawl. It points them to the download page, which is the intended route for AI use: reviewed, structured, and credited.
- **Link previews:** Open Graph title, description and image tags, so an entry shared in a chat shows a proper card. The image is generated on our own server for each entry (1200 × 630 px PNG): the `vedette` and its `sens` set in Literata on deep blue, with the Mots en commun name. It's created when the entry is saved and served as a static file. Nothing is fetched from other sites.
- **Stable addresses:** a slug never changes, even when its `vedette` is corrected, so links in lesson plans keep working.

## Technical architecture and operations

One small server in the EU runs everything. There are no external services.

| Part | Choice | Notes |
| --- | --- | --- |
| Language and framework | Python 3, Django (current long-term-support release) | Server-rendered templates, Django admin |
| Database | SQLite in WAL mode | One file, easy to back up. Move to PostgreSQL only if contributors' writes ever contend |
| History | django-simple-history | On every model, including translation tables. Shown in the admin |
| App server | Gunicorn, run by systemd |  |
| Web server | Caddy | Automatic HTTPS. Serves `/static/`, `/media/` and `/telechargements/` directly. Keeps no access logs |
| Caching | Django's cache for anonymous pages | Cleared when any record is saved |
| Sorting | PyICU, compiled against the system's ICU | Entries store an ICU sort key; `reconstruire_recherche` recomputes it after an ICU upgrade |
| Backups | Nightly SQLite online backup plus `media/`, encrypted with restic and sent to Scaleway Object Storage (Amsterdam), with a 30-day object lock | Keep 30 daily and 12 monthly. Restore tested before launch, then every six months |
| Server upkeep | Automatic security updates with reboots at 04:30 UTC, a firewall open only on 80, 443 and WireGuard, SSH by key and only through WireGuard |  |
| Admin | Non-default URL path, two-factor login required for the owner (django-otp), Argon2 passwords. See Security |  |

**Repository layout**

```
motsencommun/
  motsencommun/        settings, URLs, WSGI
  lexique/
    models.py          Entree, Piege, Exemple, Theme, LienEntree, *Traduction
    vocabulaire.py     TextChoices for every code
    recherche.py       normalisation and folding per language
    views.py  urls.py  admin.py
    management/commands/
      importer_donnees_initiales.py  import the 73 starting expressions
      exporter.py      write the download files
      reconstruire_recherche.py
    templates/lexique/
    tests/             including Ukrainian and Polish fixtures
  donnees/import/      donnees-initiales.zip
  docs/                prd.md (this document)
  locale/              en/, pl/, uk/ … .po files
  static/              one CSS file
  deploiement/         Caddyfile, systemd units, scripts, INCIDENT.md
```

Settings come from environment variables: secret key, allowed hosts, admin path, backup destination and `INSCRIPTION_SUR_INVITATION` (on by default). Nothing secret lives in the repository.

## Downloads and licence

The `/fr/telecharger/` page links to files that `python manage.py exporter` regenerates once a day, overnight, plus a dated monthly snapshot.

| File | Contents |
| --- | --- |
| `mots-en-commun.json` | Every entry, nested with its traps, examples, links and translations. Header with export date, licence and contributor credits |
| `entrees.csv`, `pieges.csv`, `exemples.csv`, `traductions.csv` | The same data as flat tables, UTF-8 with a byte-order mark |
| `dictionnaire-de-donnees.md` | Every field and code, explained in French. Contributors can translate it like everything else |

One entry in `mots-en-commun.json`, once written and reviewed, looks like this (abridged):

```json
{
  "slug": "poser-un-lapin",
  "vedette": "poser un lapin à qqn",
  "type_entree": "expression",
  "nature": "locution_verbale",
  "niveau": "B1",
  "registre": "familier",
  "sens_b1": "Ne pas venir à un rendez-vous, sans prévenir.",
  "statut": "relu",
  "ajoute_par": "Colin",
  "pieges": [
    {"type_piege": "sens_figure", "gravite": "moyenne", "concerne": ["comprehension"],
     "langue_apprenant": null,
     "explication_b1": "Rien à voir avec les lapins : la personne n'est pas venue au rendez-vous.",
     "statut": "relu"}
  ],
  "exemples": [
    {"phrase": "Il m'a posé un lapin hier soir, j'ai attendu une heure au café.",
     "surlignage": "m'a posé un lapin", "niveau": "B1",
     "traductions": {"en": "He stood me up last night. I waited an hour at the café."}}
  ],
  "traductions": {"en": {"sens": "to stand someone up", "statut": "relu"}}
}
```

**Rules**

- **Field names in the downloads are the model's French names.** `vedette`, `niveau`, `type_piege` are the public vocabulary.
- **Only reviewed content is included:** records with `statut` `relu` or `valide`, plus `retire` for anything withdrawn after publication. Drafts and records still in review stay on the site only. Every record still carries its `statut`, and a translation appears only once it's reviewed too.
- **Refused records are left out.**
- **Slugs are permanent.** A retired entry stays in the downloads marked `retire`, rather than disappearing.
- **Credit by name:** each record includes the display names of whoever added it (`ajoute_par`) and reviewed it (`relecteurs`), and the file header lists every contributor. Email addresses, accounts and the edit history never leave the server.
- **Two kinds of file:** `mots-en-commun.json` and its CSVs are rebuilt every night. On the first of each month a dated copy is also saved, for example `mots-en-commun-2026-12.json`, and kept permanently. Old snapshots are listed on the download page, so a worksheet or a study can cite the exact version it used.
- **At launch the files are empty.** The live site starts from an empty database (see the seed data section), and only reviewed entries are exported, so the files grow as the owner adds entries and reviewers approve them.

**Licence** (decided 18 November 2026):

- **Data: CC BY 4.0**, credited as *Contributeurs de Mots en commun*. Version 4.0 covers EU database rights as well as copyright.
- **Code: MIT.**
- **Pictures (phase 3) and recordings (phase 4):** also CC BY 4.0, with extra rules agreed at their gates (image sources, voice consent).

**How it's applied**

- **Contributors agree when they create an account.** A required checkbox reads *« Vos contributions sont publiées sous licence CC BY 4.0. »* ("Your contributions are published under CC BY 4.0"), and the date is stored as `licence_acceptee_le` on their profile. Contributors keep their copyright and license it to everyone.
- **The repository holds `LICENCE-DONNEES` (CC BY 4.0) and `LICENCE-CODE` (MIT).** Every page footer names the data licence and links to the credits.
- **Only original content is accepted.** Explanations and sentences must be the contributor's own words, not copied from dictionaries, textbooks or lyrics.
- **Published versions stay licensed forever.** A CC licence can't be withdrawn from a version already published, so any future change would apply to new versions only, and would need every contributor's agreement.

This isn't legal advice.

## Seed data: importing the existing 73 expressions

The earlier draft produced 73 AI-drafted items, 85 traps and 82 example sentences. They live in `donnees/import/donnees-initiales.zip`, in `data/items/*.yaml` and `data/sentences/0001-ai-placeholders.yaml`, with their format in `schema/` and a short `LISEZMOI.md`.

**They are test data only** (decided 19 November 2026). They are imported on the owner's computers and on the server during the testing phase, to try out browsing, reviewing and exporting. For go-live, the site is redeployed from an empty database without running the import, so none of this AI-drafted content reaches the live site; the owner then adds entries by hand.

`python manage.py importer_donnees_initiales <path>` loads them once, as follows:

- **Owner and status.** Everything is attributed to a system user `import-initial`, which can't log in, with `statut = brouillon`.
- **Marked as AI-generated.** Every imported record (entries, traps, examples and their links, translations, themes and links between entries) has `genere_par_ia` set. The flag can't be edited in the admin and is shown there and on reviewers' previews. During testing, seed records can be reviewed like any other.
- **English text goes to the translation layer.** The source explanations are in English, so `gloss_en`, `literal_en` and `note_en` become `EntreeTraduction` and `PiegeTraduction` rows with `langue = en`. The French `explication` stays empty until the owner writes it.
- **An empty explanation is allowed only in draft.** `explication` may be empty while `statut = brouillon`, and the model refuses `relu` or `valide` without it.
- **Example sentences become `Exemple` rows.** Each sentence becomes one `Exemple` (82 in all), linked through `ExempleEntree` to every entry its tags point to (85 links), with each tag's text as that link's `surlignage`, its position among that entry's sentences in the file as `ordre`, and the English gloss as an `ExempleTraduction`. Two sentences have no tags: they show *ça marche* and *n'importe quoi* in another sense. They are imported without links, so they can't be approved until someone links them or deletes them.
- **Labels in French** (decided 20 November 2026). `sense_label` is mostly English, and `precision` is shown in French next to the `vedette`, so the import translates it: *before the noun* → *avant le nom*, *carry out* → *accomplir*, and so on. The labels already in French (*penser à*, *X me manque*) stay as they are.

| Old field (seed files) | New field | Mapping |
| --- | --- | --- |
| `id` | `slug` | Unchanged |
| `headword` | `vedette` | Unchanged text |
| `sense_label` | `precision` | Translated into French (see above) |
| `kind` | `type_entree` | `word` → `mot`, others unchanged |
| `pos` | `nature` | `noun` → `nom`, `verb` → `verbe`, `adjective` → `adjectif`, `adverb` → `adverbe`, `conjunction` → `conjonction`, `pronoun` → `pronom`, `determiner` → `determinant`, `verb_phrase` → `locution_verbale`, `noun_phrase` → `locution_nominale`, `adjectival_phrase` → `locution_adjectivale`, `adverbial_phrase` → `locution_adverbiale`, `prepositional_phrase` → `locution_prepositionnelle`, `conjunctional_phrase` → `locution_conjonctive`, `sentence` → `phrase`; `preposition`, `numeral` and `interjection` unchanged |
| `gender` | `genre` | `m` → `masculin`, `f` → `feminin`, `plural_only` → `pluriel_seulement` |
| `ipa` | `api` | Unchanged |
| `definition_fr` | `sens` | Copied into the `sens_…` field matching the entry's `niveau` (e.g. `sens_b1`) |
| `cefr`, `register` | `niveau`, `registre` | Unchanged codes |
| `frequency` | `frequence` | `very_common` → `tres_courante`, `common` → `courante`, `uncommon` → `peu_courante` |
| `topics` | `themes` | One theme per topic, `slug` (`nom`), decided 20 November 2026: `money` → `argent` (Argent), `food` → `nourriture` (Nourriture), `work` → `travail` (Travail), `relationships` → `relations` (Relations), `emotions` → `emotions` (Émotions), `social` → `vie-sociale` (Vie sociale), `conversation` → `conversation` (Conversation), `communication` → `communication` (Communication), `time` → `temps` (Temps et durée), `weather` → `meteo` (Météo), `health` → `sante` (Santé), `home` → `maison` (Maison), `family` → `famille` (Famille), `travel` → `voyages` (Voyages), `places` → `lieux` (Lieux), `culture` → `culture` (Culture), `numbers` → `nombres` (Nombres) |
| `forms` | `formes` | Unchanged |
| `related` | `LienEntree` | `contrast` → `a_ne_pas_confondre`, `see_also` and `synonym` → `voir_aussi`, `antonym` → `contraire`, `variant` → `variante` |
| gotcha `type` | `type_piege` | `non_compositional` → `sens_figure`, `false_friend` → `faux_ami`, `partial_false_friend` → `faux_ami_partiel`, `argument_structure` → `construction_inversee`, `meaning_by_position` → `sens_selon_position`, `gender_meaning` → `sens_selon_genre`, `polarity` → `polarite`, `pronunciation` → `prononciation`, `mood_trigger` → `mode_impose`, `fixed_form` → `forme_figee`, `confusable` → `confusion_possible`, `irregular_form` → `forme_irreguliere`, `register` → `registre`, `pragmatic` → `pragmatique`; `calque`, `connotation`, `preposition` and `regional` unchanged |
| `affects`, `severity` | `concerne`, `gravite` | `low` / `medium` / `high` → `faible` / `moyenne` / `elevee` |
| `l1: en` | `langue_apprenant` | Set to `en` only for `faux_ami`, `faux_ami_partiel`, `calque`, `connotation`, `preposition` and `construction_inversee`; empty otherwise |
| `trigger`, `wrong`, `right` | `declencheur`, `incorrect`, `correct` | Unchanged |

Fields with no place in the data model are not imported: `expression_type`, `transparency`, `cefr_basis`, `detect`, `pattern`, `provenance` and `license` on entries, the trap `id`s, and the sentences' `id`, `register`, `topics`, `grammar`, `regions`, `not_tags` and `notes`.

The import runs in one transaction: an unknown code, or a tag whose text isn't in its sentence, stops it with a message naming the file and field, and nothing is imported.

The import is safe to re-run:
- **Existing entries:** it skips slugs that already exist, together with their traps and translations.
- **No duplicates:** it never creates the same example or link twice.
- **Hand-made content:** it never attaches seed content to an entry or example created by hand.
- **Deleted entries:** a seed entry that was deleted comes back with its traps, links and examples.

## Writing an entry

A short style guide, so entries read consistently whoever writes them. In phase 2 it becomes the contributor guide.

- **`vedette`:** the citation form a dictionary would print, with `qqn` / `qqch` marking slots: *poser un lapin à qqn*.
- **`sens`:** each `sens_…` field is written in French a learner at *that* level can read, without grammar jargon. Fill in the entry's own level first; lower levels can follow, written by anyone.
- **`explication`:** two or three sentences per level, following the same rule as `sens_…`: what goes wrong, then what to say or understand instead.
- **Examples:** two or three natural, everyday sentences, the shortest that show the meaning, with at least one at or below the entry's level. Never copied from books, films or songs.
- **One entry per confusing meaning:** *ancien* before and after the noun are two entries, linked as `a_ne_pas_confondre`.
- **What doesn't belong:** ordinary words with no trap, proper nouns, and content written only to shock.
- **Vulgar words and insults:** learners meet words like *putain*, *chiant* and *se foutre de* constantly, so they're included. They're labelled `registre: vulgaire`, the explanation says clearly when they offend, and the example sentences are neutral, everyday ones. Slurs that target people for their origin, religion, gender, sexuality or disability are never entries. If learners need warning about one, an explanation can describe it.
- **No inclusive-writing dots:** never write *étudiant·e·s*. It's hard for learners to read, and screen readers stumble over it. Use neutral wording (*les personnes qui apprennent*) or write both forms in full (*les étudiants et les étudiantes*).
- **Spelling:** the `vedette` uses the traditional spelling (*connaître*, *dîner*), which most textbooks use. The 1990 reformed spelling (*connaitre*, *diner*) goes in `formes`, so a search for either finds the entry.
- **Slugs:** lowercase ASCII from the `vedette`, without `qqn` / `qqch`: `poser-un-lapin`.

## Review and contribution workflow

Every entry, trap, example and translation has its own `statut`, and the history keeps every change.

| `statut` | Meaning | Who can set it |
| --- | --- | --- |
| `brouillon` | Draft: visible only to the owner and reviewers when logged in, with a *Pas encore relu* banner | The person adding it |
| `en_relecture` | Submitted for review | The person adding it |
| `relu` | Approved by one reviewer | Set by the first approving review, from a reviewer who neither added nor edited it |
| `valide` | Approved by two reviewers | Set by a second approving review, from another such reviewer |
| `refuse` | Rejected, with a comment | Set by a refusing review |
| `retire` | Withdrawn. Kept in the history and in the downloads, never deleted | The owner |

**Rules enforced by the model, not just by convention:**

- **Statuses come from reviews.** Nobody types `relu`, `valide` or `refuse`: they follow from the `Relecture` records (record, reviewer, decision, comment, date).
- **No self-review** (decided 19 November 2026). Nobody can approve a record they added *or edited*: the history shows who changed its text. So an imported entry whose French explanation the owner wrote needs another reviewer.
- **Editing a reviewed record sends it back to review** (decided 19 November 2026). Any change to the text of a `relu` or `valide` record moves it to `en_relecture`, so it leaves the public site until reviewed again, and reviews made before the change no longer count.
- **French explanations are required before approval.** `relu` and `valide` require at least one French `sens_…` level on the entry, and at least one `explication_…` level on each of its traps (refused or withdrawn traps aside). A trap needs its own `explication_…` to be approved, and an example must illustrate at least one entry.
- **A refusal needs a comment.**
- **Translations are reviewed separately.** A translation is reviewed on its own, by a reviewer whose `relit_langues` includes its language; French content needs `fr`.

**Phase 1:** the owner is the only editor. Reviewers, starting with the owner's French tutor, get accounts the owner creates by hand in the admin (invitations arrive in phase 2), and record their reviews there. During testing, the imported entries belong to `import-initial`, so the owner can review those they haven't edited, alongside the tutor. Entries the owner writes stay in `brouillon` until a second person reviews them. The site isn't announced until enough entries have been reviewed to be worth visiting.

**Phase 2:** contributors get accounts with two roles, *contributeur* and *relecteur*, built on Django's groups and permissions. They work through simple public forms rather than the admin.

**Signing up by invitation (phase 2).** At first, nobody can create an account without an invitation from the owner. Reviewers will always need one, because the owner chooses each reviewer and what they may review.

- **What an invitation is:** a code such as `MEC-7KQ4X-P2DHN` and a link that carries it, `/fr/inscription/MEC-7KQ4X-P2DHN/`. The code uses 10 random characters from an alphabet without look-alikes (no 0/O, 1/I/L), so it can also be read out or typed into the signup form.
- **Who makes them:** only the owner, in the admin. The owner shares the link any way they like (message, chat, in person); the site sends no email.
- **What the owner sets on each one:**
  - the role: `contributeur` or `relecteur`
  - for a reviewer, what they may review: `fr` for the French content, or a translation language such as `uk` or `pl` (one or more)
  - a private note saying who it's for
  - an expiry date (default 14 days)
  - for a contributor invitation only, how many times it can be used (default 1; more for a teacher's class, say). A reviewer invitation always works exactly once.
- **Signing up with it:** the form asks for a display name, email, password and the licence checkbox, as normal. The new account gets the role and review languages from the invitation, and records which invitation it used. Nobody can choose or change their own role or review languages; only the owner can, in the admin.
- **Safety:** the code is stored as a hash, like a password, so the full link is shown once, when it's created. A lost link is revoked and replaced. Wrong codes are rate-limited per address, using the cache only, so no IP log is kept.
- **In the admin:** a list of invitations showing whether each is active, used, expired or revoked, and who used it. The owner can revoke any invitation that hasn't been used.
- **Opening up later:** when `INSCRIPTION_SUR_INVITATION` is turned off, anyone can sign up as a `contributeur` without a code. Becoming a `relecteur` still needs a reviewer invitation or the owner's promotion in the admin. No public form ever grants it.

## Development workflow

- **Tests:** pytest-django, run by GitHub Actions on every push and pull request (free for public repositories). Wherever an acceptance criterion can be checked by code, it becomes a test.
- **Versions:** the current Django long-term-support release and a supported Python 3, both pinned.
- **Language of the project's conversation:** commit messages, issues and pull requests are preferably in French, but English is welcome, so contributors who don't write French easily can still take part.
- **Code contributions are open from day one.** Anyone may open a pull request. Merging needs the owner's approval and passing tests, and nobody pushes directly to the main branch (GitHub branch protection). A `CONTRIBUTING.md` explains the steps, in French first.
- **README:** `README.md` is written in French and is the source. At launch the repository also has `README.en.md`, an English translation, and no others. Both include a short section explaining that pull requests adding a translation are welcome and will be accepted if they follow the naming convention:
  - `README.<code>.md`, where `<code>` is the language's two-letter ISO 639-1 code, the same codes the site uses (`README.pl.md`, `README.uk.md`)
  - a regional variant uses a BCP 47 tag (`README.pt-BR.md`)
  - the first line says which version of `README.md` it translates, so an outdated translation is easy to spot

  The top of each README lists the translations that exist.
- **Style:** `ruff` for linting and formatting. Comments and docstrings in French, to match the names in the code.
- **Local setup:** one documented command creates the environment, runs migrations, imports the seed data and starts the server.
- **Migrations:** committed with the code, and never edited once released.
- **Dependencies:** few and pinned. Each new one needs a reason in its commit message.

## Deploying to the server

This section tells Claude Code what deployment must look like. Everything needed to set up, deploy, back up and restore lives in `deploiement/` in the repository, so the owner can rebuild the server from scratch by following its README. Scripts and comments are in French, like the rest of the code.

**Working rules for Claude Code**

- Never print, log or commit a secret. Secrets live only in `/etc/motsencommun/env` on the server, created by the owner from the `deploiement/env.exemple` template.
- Every script is idempotent: running it twice leaves the server as it was after the first run.
- Nothing is changed by hand on the server. If a change is needed, it goes into a script or config file in the repository first.
- Ask the owner before anything that can't be undone: deleting data, rotating the backup key, changing DNS.

**The server**

- A KVM VPS at LWS (French host, servers in France), with at least 2 GB RAM, 40 GB SSD, IPv4 and IPv6.
- Debian 13 if LWS offers that image, otherwise Debian 12 (upgraded in place later). Python is not taken from the system: `uv` installs the version pinned in the repository, so the Debian release doesn't matter. The server clock is UTC; Django displays times in `Europe/Paris`.
- Domain: `motsencommun.fr` (registered 19 November 2026; INPI and EUIPO searched, no conflicting trademarks). DNS: A and AAAA records for the bare domain, `www.motsencommun.fr` redirected to it, and a CAA record allowing Let's Encrypt only.

**First-time setup: `deploiement/installer-serveur.sh`**

- Creates a system user `motsencommun` that owns the app and can't log in.
- SSH accepts keys only; root login and passwords are off.
- Firewall (nftables): from the internet only ports 80, 443 and WireGuard's UDP port are open. SSH listens only on the WireGuard interface (see Security).
- Turns on unattended security updates with automatic reboots at 04:30 UTC when needed, sets up WireGuard, and adds 1 GB of swap.
- Installs Caddy from its official Debian repository, `uv` with the pinned Python version, the build packages PyICU needs (`libicu-dev`, `pkg-config`, a C++ compiler), and `gettext`, which `compilemessages` uses.
- Creates the folders below and installs the systemd units and timers.

```
/srv/motsencommun/
  versions/<tag>/      one folder per deployed release, each with its own .venv
  actuelle ->          symlink to the live release
  donnees/             base.sqlite3 and media/  (the only place the app writes)
  statique/            collectstatic output, shared across releases
  telechargements/     current download files and instantanes/AAAA-MM/
/etc/motsencommun/env  secrets and settings, mode 0640, root:motsencommun
```

**Processes (systemd)**

| Unit | What it does | When |
| --- | --- | --- |
| `motsencommun.service` | Gunicorn on a Unix socket, 3 workers, runs as `motsencommun` | always; restarts on failure |
| `motsencommun-sauvegarde.timer` | backup (see below) | every night at 02:30 UTC |
| `motsencommun-exporter.timer` | `exporter`; on the 1st of the month also the dated snapshot | every night at 03:30 UTC |
| `motsencommun-menage.timer` | `clearsessions` and a backup integrity check | weekly |

- The service is locked down: `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `NoNewPrivileges=yes`, and write access only to `donnees/` and `telechargements/`.
- If any unit fails, the owner gets a message, sent by the method set in the env file (an SMTP account or an ntfy topic).
- Django's cache must be shared between Gunicorn workers, so it uses the database or file cache, not the default per-process memory cache. The invitation rate limit depends on this.

**Caddy**

- Automatic HTTPS with Let's Encrypt, HTTP redirected to HTTPS, and zstd/gzip compression.
- Serves `/static/`, `/media/` and `/telechargements/` straight from disk. Static files with hashed names get a one-year immutable cache.
- Everything else goes to Gunicorn's socket.
- Django sets the security headers on the pages it renders, so tests can check them and embed pages can differ. Caddy adds the same headers to the files it serves itself.
- **No access logs.** Caddy and Gunicorn keep no request logs, so no visitor IP addresses are stored. Errors go to the systemd journal, which keeps 14 days.

**Deploying a release: `deploiement/deployer.sh <tag>`**

Run from the owner's machine (or by Claude Code with the owner's SSH key) once CI is green on `main`. Releases are git tags named by date, such as `v2026.11.19`.

1. Fetch the tag into `versions/<tag>/` and install dependencies from the lock file (`uv sync --frozen`).
2. Run `check --deploy --fail-level WARNING`, `collectstatic` and `compilemessages`. Stop on any error, with the live site untouched.
3. Take an online backup of the database (the same method as the nightly backup).
4. Run `migrate`, then `reconstruire_recherche`, which takes a moment and refreshes the sort keys in case the server's ICU has changed.
5. Point `actuelle` at the new release and reload Gunicorn gracefully, so no requests are dropped.
6. Check that `/sante/` and `/fr/` return 200. If not, switch `actuelle` back and reload automatically.
7. Keep the last five releases; delete older ones.

`deployer.sh --revenir` switches back to the previous release. If that release's migrations differ, the script offers to restore the backup taken in step 3 and asks for confirmation first. Migrations that delete columns or tables go in a later release than the code that stops using them, so rolling back one release is always safe.

`/sante/` is a tiny page that returns 200 when the database answers. The owner can point any uptime monitor at it.

**Backups: `sauvegarder.sh` and `restaurer.sh`**

- Copies the database with SQLite's online backup, never by copying the live file, and includes `media/` and `telechargements/instantanes/`.
- Sends it, encrypted with restic, to Scaleway Object Storage in the Amsterdam region (`nl-ams`), which is a different company and city from the LWS server. The restic password is also kept outside the server, in the owner's password manager.
- **Object lock:** the bucket is created with versioning and object lock on, and a default retention of **30 days in compliance mode**. For 30 days after a file is written, nobody (the owner included) can delete or overwrite it. restic's `forget` and `prune` work as normal: a delete only hides the file behind a delete marker, and the locked version stays recoverable.
- **Limited key:** the bucket lives in its own Scaleway project, and the server's API key can reach only that project's object storage.
- **Restoring after a break-in:** `restaurer.sh --a-la-date AAAA-MM-JJ` restores from the bucket as it was on that date (using `rclone --s3-version-at`), so backups an attacker hid can still be used. The weekly check alerts the owner if snapshots disappear unexpectedly, well within the 30 days.
- **Old hidden versions:** Claude Code checks whether Scaleway's lifecycle rules can expire non-current versions. If they can, set that to 45 days. If not, they stay, which costs cents at this size.
- Keeps 30 daily and 12 monthly backups.
- `restaurer.sh` rebuilds a working site on a fresh server from the latest backup, or a chosen one. It is tested before launch and then every six months, and the date of the last test is noted in the README.

**Phase 2 addition:** outgoing email for password resets only, through an EU SMTP provider with its credentials in the env file. Its servers are added to SPF, and it signs with DKIM.

## Security

For a small site like this, the realistic dangers are stolen logins, unpatched software and compromised dependencies, not clever attacks on the code. These requirements target those three, on top of the measures already in the deployment, privacy and technical sections. Decided 19 November 2026.

**Accounts around the site** (the owner's checklist, not code)

- Two-factor login on GitHub, LWS, Scaleway, the domain registrar and the owner's password manager. Recovery codes are kept offline, next to the restic password.
- The domain has transfer lock on (and registry lock, if the registrar offers it) and DNSSEC enabled.

**Logging in to the site**

- **Two-factor login is required from phase 1 on the owner's account**, the only superuser. It uses TOTP via django-otp, plus one-time backup codes, and no superuser can open the admin without it. Reviewers, including the tutor, are treated alike: two-factor login is available to them but not required. To keep a reviewer account low-risk, it gets only the permissions reviewing needs. It can't see or change accounts, invitations, groups or settings, and everything it changes is in the history, so misuse can be undone.
- Passwords are hashed with Argon2 (`argon2-cffi`) and must be at least 16 characters long, with no maximum below 128. Django's other password validators stay on. The form suggests a passphrase of several ordinary words, which is easier to remember at that length.
- Failed logins are slowed down per account and per address, using the shared cache only, so no IP address is stored (the same mechanism as invitation codes). After 10 failures within an hour, that account or address waits 15 minutes.
- Sessions for the owner and reviewers expire after 12 hours. Changing a password logs out every other session. Session and CSRF cookies are `Secure` and `SameSite=Lax`, and the session cookie is `HttpOnly`.

**Contributor text is never HTML**

- Everything contributors write is shown as plain text, escaped by Django's templates. No field is ever marked safe or rendered as raw HTML.
- If light formatting is ever needed, it goes through a strict allowlist renderer, decided at that point.

**Dependencies and the repository**

- Dependabot opens pull requests for updates to Python packages and GitHub Actions, and GitHub's security alerts are on.
- CI runs `pip-audit` against the locked dependencies and fails the build on any known vulnerability.
- GitHub secret scanning with push protection is on, so a commit containing a password or key is refused.
- Every GitHub Action is pinned to a full commit SHA, not a version tag.
- A new dependency is added only when it's clearly needed, and its pull request says why.

**Email in the domain's name**

- The site sends no email in phase 1, and the DNS says so: SPF `v=spf1 -all`, DMARC `p=reject` and a null MX record. Nobody can send convincing mail as `@motsencommun.fr`.
- In phase 2, the password-reset provider is added to SPF and signs with DKIM.

**Server additions** (made by `installer-serveur.sh`)

- **SSH only through WireGuard.** The server runs WireGuard, and SSH listens only on the tunnel. From the internet, only ports 80, 443 and WireGuard's UDP port answer. The script generates a WireGuard config for each of the owner's devices; private keys never leave the device they belong to. LWS's web console is the emergency way in if the tunnel breaks, and the README explains how to use it.
- Unattended upgrades reboot the server automatically at 04:30 UTC when an update needs it, after the nightly backup and export.
- Alerts go to the owner through the same channel as failed units: on **every SSH login**, when the disk is over 80% full, and when an external uptime check of `/sante/` fails.

**If a break-in is suspected: `deploiement/INCIDENT.md`**

A short runbook in French, written to be followed under stress. The principle is **rebuild, don't clean up**: since the whole server is scripted, a suspect server is replaced, not repaired.

1. Shut the server down from the LWS panel, keeping its disk in case it needs inspecting later.
2. From a device you trust, change the passwords and two-factor setup on GitHub, LWS, Scaleway and the registrar. Revoke the server's Scaleway key, its WireGuard keys and any SSH keys it held.
3. Build a new server with `installer-serveur.sh` and new secrets: a new `SECRET_KEY`, a new Scaleway key, and a new restic key (`restic key add`, then remove the old one).
4. Restore with `restaurer.sh --a-la-date` from a date before the suspected break-in. Use the history to find legitimate changes made since then, and redo them.
5. Log everyone out. If contributors' emails or password hashes may have been exposed, tell them. Under GDPR, a breach involving personal data must normally be reported to the CNIL within 72 hours.
6. Write down what happened and what changes.

The runbook is walked through during every restore test.

## Phase 1 acceptance criteria

Phase 1 is done when every item below passes. Most are automated tests.

**Data and admin**

- [ ] All models, tables, fields, URL paths, vocabulary codes and management commands use the French names in this document.
- [ ] Every model, including the translation tables, has django-simple-history. The admin shows each record's history.
- [ ] `importer_donnees_initiales` loads 73 entries, 85 traps and 82 examples (85 example links) as `brouillon`, marked `genere_par_ia`, with their English translations, and running it twice changes nothing.
- [ ] Editing the text of a reviewed record sends it back to `en_relecture`, and nobody can approve a record they added or edited.
- [ ] Saving an `Exemple` whose `surlignage` doesn't appear in `phrase` is refused with a clear message.
- [ ] Nobody can set their own record to `relu` or `valide`.

**Public site**

- [ ] Home, list, shortcut, entry, search, download and À propos pages work in French. The interface is also available in English via `/en/`.
- [ ] Filters for level, trap type, theme and register combine, and the resulting URL reproduces the same list.
- [ ] Entry pages show example sentences with `<mark>` around exactly the `surlignage` text.
- [ ] Entries, traps and examples that aren't `relu` or `valide` appear nowhere on the public site (lists, search, themes, links, embeds, sitemap, downloads), and their URLs return 404 to visitors. Logged-in reviewers see them with the *Pas encore relu* banner.
- [ ] Lists print cleanly from the browser.
- [ ] Every page works with JavaScript turned off.
- [ ] With `?mon_niveau=A2`, an entry shows the highest `sens_…` and `explication_…` versions at or below A2, and falls back to the lowest available version when none exists, saying which level is shown. Tested with an entry that only has `sens_b1`.
- [ ] The *Confort de lecture* switch changes the font to OpenDyslexic and increases size and spacing. The font file downloads only once the switch is on, the choice is remembered without a cookie, and the switch is hidden when JavaScript is off.
- [ ] Every entry has an `/integrer/` embed page, and these are the only pages another site can frame.
- [ ] `sitemap.xml` lists only reviewed entries, and reviewers' preview pages carry `noindex`. `robots.txt` lists the AI crawlers configured in settings.
- [ ] Each reviewed entry has a generated 1200 × 630 preview image, and its page carries Open Graph tags pointing to it.

**Every alphabet**

- [ ] Search ignores accents and capitals for French: *etre en train* finds *Être en train de*.
- [ ] Search ignores capitals for Cyrillic (*Київ* / *київ*) but never folds *й* into *и*. Polish *ł* is preserved.
- [ ] Ukrainian and Polish test translations display with the correct `lang` attribute and sort by their own alphabets.
- [ ] The CSV export opens in a spreadsheet with Cyrillic and Polish letters intact.

**Privacy and performance**

- [ ] A test asserts that no public page response contains a `Set-Cookie` header.
- [ ] A test asserts that no rendered public page references another domain.
- [ ] An entry page weighs under 30 KB of HTML and CSS combined.
- [ ] Pages pass an automated accessibility check (e.g. axe) with no serious issues.
- [ ] Responses carry the specified security headers: CSP with `default-src 'self'`, `frame-ancestors 'none'` (except embed pages), HSTS for one year, `Referrer-Policy` and `Permissions-Policy`.

**Operations**

- [ ] `exporter` writes all download files, and `/fr/telecharger/` links to them.
- [ ] `deploiement/` holds `installer-serveur.sh`, `deployer.sh`, `sauvegarder.sh`, `restaurer.sh`, the Caddyfile, systemd units and timers, `env.exemple` and a README. `installer-serveur.sh` sets up a fresh Debian 13 server, and running it a second time changes nothing.
- [ ] Settings come from environment variables, and the admin lives at a configurable path.
- [ ] The repository contains `LICENCE-DONNEES` (CC BY 4.0) and `LICENCE-CODE` (MIT), and every page footer names the data licence.
- [ ] Downloads contain only `relu`, `valide` and `retire` records, with contributors' display names and no emails. A dated snapshot is saved on the first of each month and kept.
- [ ] `SECURITY.md` and `/.well-known/security.txt` point to GitHub's private vulnerability reporting. CI runs the tests on every push, and the main branch is protected.
- [ ] `deployer.sh` deploys a tag without dropping requests, and switches back by itself when `/sante/` fails after the switch (tested by deploying a deliberately broken tag to a test server).
- [ ] `manage.py check --deploy` gives no warnings on the server. HTTP redirects to HTTPS, the site answers over IPv4 and IPv6, and the SSL Labs grade is A or better.
- [ ] Neither Caddy nor Gunicorn writes access logs, and the journal keeps errors for 14 days.
- [ ] Before launch, `restaurer.sh` has rebuilt the site on a fresh server from the off-site backup, and the README notes the date and how long it took.
- [ ] A superuser can't open the admin without passing a TOTP check, tested with a logged-in superuser who has no device set up. A reviewer account opens it without two-factor login, but can't see accounts, invitations, groups or settings.
- [ ] Passwords are stored with Argon2 and need at least 16 characters (a 15-character password is refused), repeated failed logins are slowed down, and staff sessions expire after 12 hours. Each is covered by a test.
- [ ] A test saves `<script>alert(1)</script>` in every contributor text field and finds it escaped on every page that shows it.
- [ ] CI runs `pip-audit` and fails on a known vulnerability. Dependabot and secret scanning with push protection are on, and every Action is pinned to a commit SHA.
- [ ] From the internet, only ports 80, 443 and WireGuard's port answer, and SSH works only through the tunnel. An SSH login sends the owner an alert.
- [ ] DNS has DNSSEC, CAA, SPF `-all`, DMARC `p=reject` and a null MX record, and the domain has transfer lock on.
- [ ] `deploiement/INCIDENT.md` exists and was walked through during the pre-launch restore test.

## Later

Ideas that are agreed but not yet scheduled into a phase.

- [ ] **Live level checking while writing explanations.** When a contributor types a `sens_…` or `explication_…` text, every word above that field's level is underlined as they type. For example, *indépendamment* would be flagged in `sens_a2`. This needs:
  - a `Mot` table (`lemme`, `niveau`, `source`), filled in gradually as words get tagged with their level
  - a French lemmatiser, so that inflected forms (*allions*, *veuille*) match their dictionary form
  - a small script on the editing screens only; public pages are unaffected

  FLELex's CEFR word levels could seed the `Mot` table. Its licence is non-commercial (CC BY-NC), which a non-commercial project can use internally, but its data must never be copied into the CC BY downloads. Check the licence terms before using it.

## Risks

| Risk | Mitigation |
| --- | --- |
| The 73 imported entries were drafted by AI and may contain errors | Used for testing only, marked `genere_par_ia`; the live site is deployed from an empty database without them |
| Explanations written by a learner (the owner) contain mistakes | Same review rule: nothing the owner writes reaches `relu` without a second person |
| French-only explanations are too hard for beginners at launch | The English layer comes from the import; the owner and friends add Polish and Ukrainian over time |
| Self-hosting upkeep (updates, backups, security) gets neglected | Automatic security updates; one backup script with a tested restore; a short checklist in `deploiement/README` |
| Spam or vandalism once contributors join (phase 2) | Accounts by invitation at first; every change reviewed; full history makes rollback easy |
| Pictures with unclear rights (phase 3) | Only the contributor's own work, or CC0 / CC BY images, with `credit` and `licence` required on every `Illustration` |
| Voice recordings are personal data (phase 4) | Explicit consent recorded per file, a clear voice licence, deletion on request, moderation before publishing |
| Scope creep towards a full dictionary | Non-goals stated above: an entry belongs only if it trips learners up |

## Open questions

- [ ] **Reviewers:** the owner's French tutor is the first reviewer. Who else, among native speakers, will review? (How they join is settled: by a reviewer invitation.)
