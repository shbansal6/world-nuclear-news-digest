# World Nuclear News Digest

An independent, source-linked research archive drawing on public [World Nuclear News](https://www.world-nuclear-news.org/) reporting, with a website design inspired by the Neutron Bytes tracker.

**Planned public URL:** https://shbansal6.github.io/world-nuclear-news-digest/

## Coverage

| Year | Organization |
| --- | --- |
| 2024 | 4 quarterly archives (Q1–Q4) |
| 2025 | 12 monthly archives |
| 2026 | Monthly archives to the present |
| Weekly Updates | Detailed Monday briefings, reverse chronological, with a weekly sidebar |

The archive uses a consistent industry classification: new build and milestones, SMRs and advanced reactors, nuclear PPAs/offtake, existing fleet and restarts, uranium/fuel, policy/regulation, corporate/financing, waste/decommissioning, and fusion/research. Every record links to the original WNN article first and adds other sourced hyperlinks when verified.

## Automatic Monday update

The GitHub Actions workflow [Refresh and publish nuclear digest](.github/workflows/refresh.yml) is configured for **Mondays at 7:00 AM America/Chicago**, automatically adjusting between CST and CDT. It also refreshes on source/workflow changes and can be run manually.

It performs the following:
1. Finds article URLs in WNN public RSS and XML sitemap, without a paid API, key or LLM API.
2. Extracts article dates, concise attributed descriptions and direct sources; classifies each item and retains a limited selection of material articles per historical period.
3. Keeps **all verified in-scope articles**, without a 48-article monthly or 75-article quarterly cap, and assigns multiple contextual technology and commercial tags; materiality scores are for optional sorting, never inclusion.
4. Maintains a globally searchable archive with year/month/technology/category filters and up to seven September-2026-onward weekly editions, including a researched October 12–18 issue.
4. Preserves hand-researched editorials (which are marked editorial) rather than replacing them with automatic summaries.
5. Commits refreshed JSON data into the main branch and deploys GitHub Pages.

**Editorial distinction:** The initial Oct 12–18, 2026 briefing is hand-researched; automatically generated issues are attributed article roundups, not original analytical reporting. This service does not independently verify each report and does not claim affiliation with WNN. Historical backfilling depends on the public source sitemap availability; sparse or missing periods will be shown transparently rather than populated with fabricated stories.

## Required one-time GitHub settings

1. Open [Settings → Pages](https://github.com/shbansal6/world-nuclear-news-digest/settings/pages).
2. Select **Build and deployment → Source: GitHub Actions**.
3. Ensure repository Actions are enabled, with workflow permission to write repository contents (the workflow explicitly requests contents: write).
4. Open [Actions](https://github.com/shbansal6/world-nuclear-news-digest/actions) and select **Refresh and publish nuclear digest → Run workflow**. The first run performs the historical backfill and deploys the site.

The Pages site will not be accessible until publishing is enabled and a deployment has succeeded.

## Stack

HTML, CSS, vanilla JavaScript; Python with BeautifulSoup and Requests; GitHub Actions/Pages. All article copyrights remain with original publishers; summaries are brief and link to the source. No externally provisioned services, API keys or database are required.

To check or change the selection cap, edit scripts/refresh.py. Archive content lives in data/articles.json and weekly reports in data/briefings.json.

## October 2026 Google–Constellation completeness check
The October 6 Google–Constellation 20-year PPA (890 MW of proposed uprates) and Oracle–Point Beach reporting is included under its WNN source URL. Source-verified tags/aliases for this article and the Amazon–Constellation deal are maintained in `data/editorial_overrides.json`, so later automatic refreshes do not omit significant transaction classifications in generic-headline reports. This is not a general substitute for checking completeness against all published WNN articles.

## Integration and limitations
The website is a plain static site. To update a live Vercel deployment, that Vercel project must be Git-linked to this repository's `main` branch. The archive JSON may be larger than the 1 MB GitHub Contents API fetch limit; GitHub workflows clone it normally, while other GitHub clients may need the Git Blob API. Public RSS and sitemaps may omit articles; discovery is tracked and improved over subsequent scheduled runs. The UI searches **the entire stored archive** (including named entities), not the publisher's live full-text website.
