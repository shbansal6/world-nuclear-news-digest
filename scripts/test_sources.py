#!/usr/bin/env python3
"""Regression tests: NCEA source filter must not mix in general energy reports."""
import datetime as dt
from sources import NCEA_LIBRARY, ncea_reports

LISTING = '''<main>
<a href="/research/nuclear-workforce">Workforce</a>
<a href="/research/oil-markets">Oil markets</a>
<a href="/research/no-date">No date</a>
<a href="/research/future">Future study</a>
</main>'''

def detail(title,topics,date,description):
    dateline=f'<p>{date}</p>' if date else ''
    return (f'<html><head><meta property="og:title" content="{title} — NCEA">'
            f'<meta name="description" content="{description}"></head>'
            f'<body><main><p>{title}</p><p>Brief summary about nuclear sector conditions.</p>'
            f'<p>{topics}</p><p>Issue Brief</p>{dateline}'
            f'<p>Publication details and substantive analysis continue here.</p></main></body></html>')

PAGES = {
 NCEA_LIBRARY:LISTING,
 'https://energyanalytics.org/research/nuclear-workforce':detail(
    'The Nuclear Workforce: An Essential Energy Priority Facing the Nation',
    'Nuclear Energy', 'May 28, 2026',
    'This study examines the workforce requirements for reactor restarts, nuclear power uprates and new nuclear construction.'),
 'https://energyanalytics.org/research/oil-markets':detail(
    'Oil Markets and the Future of Energy Policy',
    'Oil & Gas', 'April 2, 2026',
    'This broad energy market report mentions nuclear energy as a potential comparison in its later analysis.'),
 'https://energyanalytics.org/research/no-date':detail(
    'Reactor Research Lacking a Verified Publication Date',
    'Nuclear Energy', '',
    'A nuclear-related report without any publisher-supported publication date must not be indexed in the dated archive.'),
 'https://energyanalytics.org/research/future':detail(
    'Future Nuclear Energy Prospects and Policy',
    'Nuclear Energy', 'December 15, 2027',
    'This future-dated report should not appear in the current archive because its publication is in the future.'),
}

def fetch(url):
    return PAGES.get(url,'').encode('utf-8')

def main():
    records=ncea_reports(fetch)
    assert len(records)==1, f'Expected exactly one eligible NCEA research record, got {len(records)}'
    r=records[0]
    assert r['url'].endswith('/research/nuclear-workforce')
    assert r['date']=='2026-05-28'
    assert r['kind']=='report'
    assert r['publisher_topics']==['Nuclear Energy']
    assert 'workforce' in r['summary'].lower()
    print('NCEA regression: strict publisher topic/date validation PASS')

if __name__=='__main__':
    main()
