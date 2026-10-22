# Nuclear Intelligence — news and research archive

A source-attributed nuclear-sector research website, built on the existing World Nuclear News digest. The live application preserves the existing editorial visual design and month/year navigation.

**Production site:** https://world-nuclear-news-digest.vercel.app/

## Source policy

| Publisher | Content role | Ingestion |
| --- | --- | --- |
| World Nuclear News (WNN) | Global nuclear news | Public RSS + publisher XML sitemap; dated article pages |
| American Nuclear Society (ANS) Nuclear Newswire | Nuclear news | Official RSS https://www.ans.org/news/feed/ |
| Nuclear Innovation Alliance (NIA) Resources | Reports and policy research | Resources listing, **Reports**-marked publications only |
| Breakthrough Institute — Nuclear Energy Innovation | Nuclear research and analysis | Published research pages, verifying each date and abstract |
| National Center for Energy Analytics (NCEA) | Nuclear energy studies, issue briefs and policy research | [Publisher's Nuclear Energy library](https://energyanalytics.org/research-library?topic_equal=Nuclear+Energy); verify **each document's Nuclear Energy tag, original date and description** (the filtered URL can still expose unrelated studies in page HTML) |

The separate Neutron Bytes feed is excluded entirely. Do not ingest it in this application.

Content categories are **News** and **Research reports**; both appear in the single latest-first main archive. Research reports also have a dedicated filter and a **New research reports** section within the appropriate dated weekly briefing. Each report includes a source-linked title and a plain description of the publication's contents.

## Event-level duplicate policy

- Normalize exact URL aliases. For WNN and ANS **news** in a ten-day event window, compare title and summary overlap, named transaction participants, MW/GW values, dates and event stage. The thresholds are intentionally conservative; if uncertain, preserve both rather than silently suppressing a distinct development.
- Never collapse news about *different* customers, PPAs, plants, permits, approvals, construction starts or operating milestones just because company or project names overlap.
- Prefer WNN as the canonical summary when two reports describe the same event; retain ANS's actual article as `alternate_sources` and surface its link on the news card.
- Independent research is **never** deduplicated away as a news article. Revisions and substantive new analyses should remain discoverable as their own publications.
- Preserve alternate links across recurring refreshes; the deduplicator eliminates repeated alternates.

## Taxonomy and filtering

Technology tags: Traditional fission, Advanced fission, Microreactors, Fusion.

Activity tags: Restarts & uprates; Offtakes & customers; Construction & licensing; Fuel & supply chain; Capital & financing; Policy & international.

Records can have more than one technology and activity tag. Filtering works across **every loaded archive record before pagination**, including company names, summaries, source and alternate-publisher metadata. Additional filters are publisher, content type and offtaker/customer, with Google/Alphabet, Amazon/AWS, Microsoft, Meta and Oracle grouped under consistent names.

Export **Copy links** provides the filtered article list for presentation research; **Export CSV** includes date, title, publisher, record type, tags, original URL and additional source URLs.

## Scheduled publishing

The workflow [Refresh and publish nuclear digest](.github/workflows/refresh.yml) runs each Monday at **7:00 AM America/Chicago** (both UTC offsets, with a local DST guard). It discovers new source records, preserves existing historical content on network errors, merges repeated WNN/ANS events, reapplies verified editorial overrides, rebuilds news/reports weekly sections, checks archive integrity, and publishes static files.

A separate weekly editorial ChatGPT task has the same Monday schedule. It may enrich the research commentary, but must re-read the latest repository data to avoid overwriting concurrent automated publisher discoveries. Human-researched weekly editions are retained, with new dated research reports merged in.

Safeguards:
- No materiality cutoff or arbitrary news cap.
- No guessed publication dates, report names or article URLs.
- No replacement of historical records with blank data after source failures.
- GitHub Actions runs Python compilation, [dedupe regression tests](scripts/test_dedupe.py), archive/transaction integrity checks, JavaScript syntax checking and a UI smoke test before committing an updated archive.
- If a publisher changes its page format, report the resulting ingestion gap rather than claim complete coverage.
- Existing WNN historical archives begin in January 2024. ANS's official RSS only supplies its retained feed window; **a full historical ANS backfill is not yet complete**.

## Stack and limits

HTML, CSS, vanilla JS; Python Requests, BeautifulSoup and XML; GitHub Actions; Vercel with a Git-linked main branch. This independent site is not affiliated with its publishers. Keep publisher excerpts concise and link to originals. Publisher availability, metadata completeness and changing page layouts constrain historical coverage. NCEA uses the user-confirmed **Nuclear Energy** research library and a strict per-document topic/date check. Since the library HTML can include unrelated energy studies, never trust the query parameter alone.

### Files

- `data/articles.json`: all indexed records and report descriptions
- `data/briefings.json`: weekly briefings, latest first
- `data/editorial_overrides.json`: verified transaction-specific overrides
- `scripts/refresh.py`: orchestrator and WNN collector
- `scripts/sources.py`: ANS/NIA/Breakthrough source adapters
- `scripts/dedupe.py`: real-world WNN/ANS news-event reconciliation
- `scripts/taxonomy.py`: named entities, technology and activity tags
- `scripts/audit.py`, `scripts/test_dedupe.py`, `scripts/smoke.js`: publishing checks
