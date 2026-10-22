#!/usr/bin/env python3
"""WNN public-source collector. No commercial/news/LLM APIs or access tokens.
Uses WNN's public sitemap, RSS feed and articles. Only brief abstracts are stored.
All data is directly linked and attributed; no claims of original reporting.
"""
import concurrent.futures
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from taxonomy import enrich_record
from comprehensive_sources import collect_all_sources as collect_other_sources, canonical_url
from dedupe import reconcile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://www.world-nuclear-news.org"
TODAY = dt.datetime.now(ZoneInfo("America/Chicago")).date()
START = dt.date(2024, 1, 1)
END = TODAY
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "WNN-Research-Digest/1.0 (+source-attributed public news links; GitHub Pages)", "Accept": "text/html, application/rss+xml, application/xml, text/xml"})
DATE_PATTERN = re.compile(r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})')
MONTHS = {m.lower(): n for n, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"],1)}
PRIORITY = re.compile(r'\b(?:commission|criticality|first power|grid|commercial operation|groundbreaking|ground-breaking|construction|permit|licen[cs]|approv|agreement|offtake|ppa|purchase|funding|investment|financ|restart|uprate|contract|deal|fuel|uranium|enrich|haleu|smr|reactor|power plant|milestone|signed|reopens|begins operations|startup)\b',re.I)
CORPORATE = re.compile(r'\b(?:stake|acqui|invest|funding|finance|financing|merger|shareholder|ipo|equity|contract awards|joint venture)\b',re.I)
OFFTAKE = re.compile(r'\b(?:power purchase|ppa|offtake|electricity supply|buy power|purchase power|energy supply agreement)\b',re.I)
FUEL = re.compile(r'\b(?:uranium|haleu|enrich|conversion|fuel|centrifuge|mine|mining|triso)\b',re.I)
POLICY = re.compile(r'\b(?:government|policy|legislation|law|regulator|permit|licen[cs]|approval|nrc|iaea|safety)\b',re.I)
WASTE = re.compile(r'\b(?:waste|recycling|decommission|repository|storage|spent fuel)\b',re.I)
FUSION = re.compile(r'\b(?:fusion|tokamak|stellarator|plasma)\b',re.I)
RESTART = re.compile(r'\b(?:restart|reopen|uprate|life extension|extended operation|refurbishment|outage|recommission)\b',re.I)
SMR = re.compile(r'\b(?:smr|microreactor|micro-reactor|advanced reactor|modular|molten salt|pebble bed|fast reactor|kairos|oklo|x-energy|nuscale)\b',re.I)

def fetch(uri, timeout=25):
    for attempt in range(2):
        try:
            r = SESSION.get(uri, timeout=timeout)
            if r.status_code == 200 and r.content:
                return r.content
        except requests.RequestException:
            pass
        if attempt == 0:
            time.sleep(.5)
    return b""

def abs_url(s):
    try:
        u = urllib.parse.urljoin(BASE, s)
        p = urllib.parse.urlparse(u)
        if p.scheme != 'https' or p.hostname not in ('world-nuclear-news.org','www.world-nuclear-news.org'):
            return ''
        return urllib.parse.urlunparse(('https','www.world-nuclear-news.org',p.path.rstrip('/'),'', '', ''))
    except Exception:
        return ''

def parse_date(s):
    if not s:
        return None
    if m := DATE_PATTERN.search(s):
        try: return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
        except (ValueError, KeyError): pass
    try:
        x = dt.date.fromisoformat(str(s)[:10])
        return x
    except (ValueError, TypeError): pass
    try: return email.utils.parsedate_to_datetime(s).date()
    except (ValueError, TypeError, IndexError): return None

def category(title, text, orig=''):
    s = title + ' ' + text[:250]
    name = orig.lower()
    if OFFTAKE.search(s): return 'Nuclear PPAs & offtake'
    if FUSION.search(s) or 'fusion' in name: return 'Fusion & research'
    if WASTE.search(s) or 'waste' in name: return 'Waste & decommissioning'
    if FUEL.search(s) or 'uranium' in name: return 'Uranium & fuel'
    if RESTART.search(s): return 'Operations & restarts'
    if POLICY.search(s) and ('regulation' in name or 'policy' in name or 'government' in name): return 'Policy & regulation'
    if CORPORATE.search(s) or 'corporate' in name: return 'Corporate & financing'
    if SMR.search(s): return 'SMRs & advanced reactors'
    if POLICY.search(s) and re.search(r'\b(?:policy|nrc|iaea|government|regulation|law)\b',title,re.I): return 'Policy & regulation'
    if 'new nuclear' in name or re.search(r'\b(?:unit|reactor|plant|build|construction|commission|grid|project)\b',s,re.I): return 'New build & milestones'
    return 'Other nuclear'

def shorten(s, limit=365):
    s = re.sub(r'\s+',' ',html.unescape(s or '')).strip()
    if len(s) <= limit: return s
    return s[:limit].rsplit(' ',1)[0].rstrip(' ,;:')+'…'

def parse_article(u):
    raw = fetch(u)
    if not raw: return None
    soup = BeautifulSoup(raw, 'html.parser')
    h1 = soup.find('h1')
    if not h1: return None
    title = h1.get_text(' ',strip=True)
    if not title or len(title) > 220: return None
    # Prefer structured publication metadata; fall back to the date rendered next to the title.
    date = None
    for attr, val in [('property','article:published_time'),('name','datePublished'),('itemprop','datePublished')]:
        tag = soup.find('meta',attrs={attr:val})
        if tag: date = parse_date(tag.get('content'))
        if date: break
    if not date:
        for script in soup.find_all('script',type='application/ld+json'):
            try:
                j = json.loads(script.string or script.get_text() or '{}')
                seq = j if isinstance(j,list) else [j]
                for item in seq:
                    if isinstance(item,dict) and item.get('datePublished'):
                        date = parse_date(item['datePublished'])
                        break
            except (ValueError, TypeError): pass
            if date: break
    if not date:
        for elt in list(h1.next_elements)[:35]:
            txt = elt.strip() if isinstance(elt,str) else ''
            if txt and (date := parse_date(txt)): break
    if not date or not (START <= date <= END): return None
    description = ''
    tag = soup.find('meta',attrs={'name':'description'})
    if tag: description = (tag.get('content') or '').strip()
    if len(description) < 55 or 'world nuclear news' in description.lower()[:100]:
        for p in h1.find_all_next(['p'], limit=14):
            t = p.get_text(' ',strip=True)
            if len(t)>65 and 'cookie' not in t.lower() and 'newsletter' not in t.lower():
                description=t; break
    if not description: return None
    # Only capture hyperlinks appearing between the article title and its news-sidebar sections.
    # Never mistake 'Most Read' or general site navigation for a cited primary source.
    links=[]
    for node in h1.next_elements:
        if isinstance(node,str) and node.strip().lower() in ('most read','related information','related stories','newsletter subscription'):
            break
        if getattr(node,'name',None) in ('h2','h3','h4'):
            heading=node.get_text(' ',strip=True).lower()
            if heading in ('most read','related information','related stories','podcasts & features'):
                break
        if getattr(node,'name',None)!='a' or not node.has_attr('href'):
            continue
        href=urllib.parse.urljoin(BASE,node['href'].strip())
        p=urllib.parse.urlparse(href)
        if p.scheme!='https' or not p.hostname or href.rstrip('/')==u.rstrip('/'):continue
        if any(bad in p.path.lower() for bad in ('privacy','cookie','newsletter','facebook','twitter','linkedin')):continue
        label=shorten(node.get_text(' ',strip=True) or p.hostname,45)
        if not label:continue
        if href not in [z['url'] for z in links]:links.append({'label':label,'url':href})
        if len(links)==3:break
    # Prevent category detection from unrelated footer/navigation.
    orig = ''
    section = soup.find('meta',attrs={'property':'article:section'})
    if section:orig=section.get('content','')
    # Extract context for entity recognition and tags without redistributing article text.
    paras=[]
    for p in h1.find_all_next('p',limit=18):
        val=p.get_text(' ',strip=True)
        if len(val)>35 and not any(q in val.lower() for q in ('cookies policy','subscribe to our newsletter')):paras.append(val)
    record={'date':date.isoformat(),'title':title,'summary':shorten(description),'category':category(title,description,orig),'url':u,'links':links,'source':'World Nuclear News'}
    record['coverage_detail']=len(' '.join(paras[:14]))+len(description)
    return enrich_record(record,' '.join(paras[:14]))

def crawl_sitemaps():
    pending=[BASE+'/sitemap.xml']
    seen=set(); found={}
    while pending and len(seen)<80:
        current=pending.pop(0)
        if current in seen:continue
        seen.add(current)
        raw=fetch(current,timeout=40)
        if not raw:continue
        try: root=ET.fromstring(raw)
        except ET.ParseError:continue
        tag=root.tag.split('}')[-1].lower()
        if tag=='sitemapindex':
            for item in root:
                loc=next((z.text for z in item if z.tag.endswith('loc')),None)
                if loc and loc not in seen:pending.append(loc)
        elif tag=='urlset':
            for item in root:
                loc=next((z.text for z in item if z.tag.endswith('loc')),None)
                last=next((z.text for z in item if z.tag.endswith('lastmod')),None)
                if not loc:continue
                path=urllib.parse.urlparse(loc).path.lower()
                if not path.startswith('/articles/'):continue
                d=parse_date(last)
                if d and d.year<2024:continue
                u=abs_url(loc)
                if u:found[u]=d
    print('Sitemap files:',len(seen),'article candidates:',len(found),flush=True)
    return found

def crawl_rss():
    raw=fetch(BASE+'/rss')
    if not raw:return {}
    try:root=ET.fromstring(raw)
    except ET.ParseError:return {}
    results={}
    for item in root.findall('.//item'):
        loc=item.findtext('link')
        if loc:
            u=abs_url(loc)
            if u and '/articles/' in u.lower():results[u]=None
    print('RSS articles:',len(results),flush=True)
    return results

def read_source_records():
    """Source-level archive is separate from event-level deduplicated display.
    Preserve each publisher link/title/summary even when two news stories match.
    """
    path=DATA/'source_records.json'
    if path.exists():
        payload=json.loads(path.read_text(encoding='utf-8'))
        records=payload if isinstance(payload,list) else payload.get('records',[])
        if records:return records
        raise RuntimeError('Refusing to replace an empty source-level archive')
    # Migration from the existing display archive; canonical event records and
    # their alternate-source provenance are not discarded. Previous alternates
    # may have title+URL only, until backfill retrieves original abstracts.
    return read_articles()

def read_articles():
    p=DATA/'articles.json'
    if not p.exists():return []
    j=json.loads(p.read_text(encoding='utf-8'))
    return j if isinstance(j,list) else j.get('articles',[])


def canonicalize_source_records(records):
    """Unify NIA's /index.php/ aliases without losing original link provenance.

    Multiple URLs that resolve to the same NIA document are a *single*
    source publication, even when separately discovered via resources and
    News & Blog. Keep both original URLs in source_url_aliases.
    """
    by_url={}
    for source in records:
        if not source.get('url') or not source.get('date'):continue
        a=dict(source)
        old=a['url'].rstrip('/')
        parsed=urllib.parse.urlparse(old)
        u=canonical_url(old) if parsed.hostname in (
            'nuclearinnovationalliance.org','www.nuclearinnovationalliance.org'
        ) else old
        a['url']=u
        aliases=list(a.get('source_url_aliases') or [])
        if old!=u:aliases.append(old)
        if u in by_url:
            prev=by_url[u]
            def rank(z):return (bool(z.get('publication_type')),len(z.get('summary','')))
            keep=a if rank(a)>rank(prev) else prev
            aliases+=list(prev.get('source_url_aliases') or [])
            aliases+=list(a.get('source_url_aliases') or [])
            if keep is a and prev.get('alternate_sources') and not keep.get('alternate_sources'):
                keep['alternate_sources']=prev['alternate_sources']
            a=keep
        aliases=[v for v in dict.fromkeys(aliases) if v.rstrip('/')!=u]
        if aliases:a['source_url_aliases']=aliases
        else:a.pop('source_url_aliases',None)
        by_url[u]=a
    return by_url

def bucket(a):
    d=a['date']
    if d[:4]=='2024':return d[:4]+'-Q'+str((int(d[5:7])-1)//3+1)
    return d[:7]

def select_candidates(found, existing):
    """Fetch every in-scope article; no monthly or quarterly inclusion quotas.
    Bound one Actions execution to 3,000 unindexed URLs, not a per-period record cap.
    Future weekly runs continue backfilling pending published URLs.
    """
    dated=[];undated=[]
    for u,d in found.items():
        if u in existing:continue
        if d is not None:
            if d.year<2024:continue
            dated.append((d,u))
        else:undated.append(u)
    dated.sort(reverse=True)
    # Important: missing dates in a sitemap should not prevent discovery of articles.
    pending=list(dict.fromkeys([u for _,u in dated]+undated))
    batch=pending[:3000]
    print('Pending in-scope candidate pages:',len(pending),'fetch this run:',len(batch),flush=True)
    return batch


def build_briefs(stories):
    """Every Monday covers the preceding complete Monday-Sunday week.

    Each real-world news event occurs once; each newly published research report
    has its own named section with a description of its actual contents.
    """
    last_monday=TODAY-dt.timedelta(days=TODAY.weekday())
    output=[]
    earliest=max(dt.date(2026,9,7),last_monday-dt.timedelta(days=7*6))
    monday=last_monday
    while monday>=earliest:
        start=monday-dt.timedelta(days=7)
        finish=monday-dt.timedelta(days=1)
        selection=[a for a in stories if start.isoformat()<=a['date']<=finish.isoformat()]
        if selection:
            grouped=defaultdict(list)
            news=[a for a in selection if a.get('kind','news')!='report']
            reports=[a for a in selection if a.get('kind')=='report']
            for a in sorted(news,key=lambda z:z['date'],reverse=True):
                grouped[(a.get('categories') or [a.get('category','Other nuclear')])[0]].append(a)
            sections=[]
            if reports:
                reports.sort(key=lambda a:(a['date'],a['title']),reverse=True)
                sections.append({'category':'New research reports',
                    'takeaway':str(len(reports))+' new source-attributed nuclear research publication(s) released this week. Each entry describes what the publication covers.',
                    'items':reports})
            for cat,items in sorted(grouped.items(),key=lambda kv:-len(kv[1])):
                examples='; '.join(x['title'] for x in items[:2])
                sections.append({'category':cat,'takeaway':f'{len(items)} distinct development(s), including {examples}.','items':items})
            output.append({'week_start':start.isoformat(),'week_end':finish.isoformat(),
                'title':'Global nuclear developments — week of '+start.strftime('%B %-d, %Y'),
                'overview':f'{len(news)} distinct nuclear news events and {len(reports)} newly released research reports from monitored publishers; all have original source links.',
                'article_count':len(selection),'report_count':len(reports),
                'generated_at':TODAY.isoformat(),'sections':sections})
        monday-=dt.timedelta(days=7)
    return output
def add_reports_to_editorial(editorial,generated):
    """Keep human-authored commentary, but don't omit new reports from its dated issue."""
    by_week={x['week_start']:x for x in generated}
    for week,issue in editorial.items():
        auto=by_week.get(week)
        if not auto:continue
        report_section=next((x for x in auto.get('sections',[]) if x.get('category')=='New research reports'),None)
        if not report_section:continue
        current=list(issue.get('sections') or [])
        seen={item.get('url') for section in current for item in section.get('items',[])}
        fresh=[a for a in report_section['items'] if a.get('url') not in seen]
        if not fresh:continue
        existing=next((x for x in current if x.get('category')=='New research reports'),None)
        if existing:
            existing['items'].extend(fresh)
        else:
            current.insert(0,{'category':'New research reports','takeaway':'Recently published research and policy analysis from monitored organizations.','items':fresh})
        issue['sections']=current
        issue['report_count']=len(report_section['items'])
        issue['article_count']=sum(len(x.get('items',[])) for x in current)

def main():
    # Scheduled workflow runs twice around US DST transition, but only the local 7am run updates.
    if os.getenv('GITHUB_EVENT_NAME')=='schedule' and dt.datetime.now(ZoneInfo('America/Chicago')).hour!=7:
        print('Not 7am Central; other DST cron handles this date.');return
    DATA.mkdir(exist_ok=True)
    old=read_source_records()
    if len(old)<1000:raise RuntimeError('Refusing suspicious contraction of historical nuclear archive')
    existing=canonicalize_source_records(old)
    # Remove prior duplicate display cards before merging fresh source material.
    # Alternate source URLs stay attached to the canonical story.
    available=crawl_rss()
    available.update(crawl_sitemaps())
    todo=select_candidates(available,existing)
    changed=0
    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            for rec in pool.map(parse_article,todo):
                if rec:
                    existing[rec['url']]=rec;changed+=1
    print('New WNN articles:',changed,flush=True)
    for rec in collect_other_sources(fetch):
        original=rec['url'].rstrip('/')
        host=urllib.parse.urlparse(original).hostname
        u=canonical_url(original) if host in (
            'nuclearinnovationalliance.org','www.nuclearinnovationalliance.org'
        ) else original
        rec['url']=u
        if original!=u:
            rec['source_url_aliases']=list(dict.fromkeys(
                list(rec.get('source_url_aliases') or [])+[original]))
        if u not in existing:
            existing[u]=rec
            changed+=1
        else:
            prev=existing[u]
            if (bool(rec.get('publication_type')),len(rec.get('summary','')))>(
                bool(prev.get('publication_type')),len(prev.get('summary',''))):
                aliases=list(dict.fromkeys(
                    list(prev.get('source_url_aliases') or [])+
                    list(rec.get('source_url_aliases') or [])))
                if aliases:rec['source_url_aliases']=aliases
                existing[u]=rec
    print('Total new verified source records:',changed,flush=True)
    # Store every distinct publisher publication BEFORE reconciling public
    # cards. A canonical event can then link to its complete sources without
    # destructively deleting an independent publisher's record.
    originals=sorted(existing.values(),key=lambda r:(r['date'],r.get('source',''),r['url']),reverse=True)
    groups=defaultdict(list)
    for a in existing.values():
        d=parse_date(a.get('date'))
        if d and START<=d<=END and a.get('url') and a.get('title'):
            groups[bucket(a)].append(a)
    # Completeness first: keep all verified, distinct reports from all target periods.
    selected=list({a['url']:a for items in groups.values() for a in items}.values())
    # Reconcile overlapping WNN and ANS reporting AFTER source collection.
    selected=reconcile(selected)
    for a in selected:
        # A source-fetched record has already been tagged with article-body context.
        # Do not retag it later using its generic headline/abstract alone.
        if not a.get('categories') and not a.get('technologies'):
            enrich_record(a)
    try:
        edits=json.loads((DATA/'editorial_overrides.json').read_text(encoding='utf-8')).get('articles',{})
    except (OSError,ValueError,AttributeError):
        edits={}
    for a in selected:
        edit=edits.get(a.get('url'))
        if edit:
            a['technologies']=edit['technologies']
            a['categories']=edit['categories']
            a['entities']=list(dict.fromkeys((a.get('entities') or [])+edit.get('entities',[])))
            a['search_text']=edit.get('search_text','')+' '+' '.join(a['entities'])
    selected.sort(key=lambda a:(a['date'],a.get('importance_score',0)),reverse=True)
    briefings=build_briefs(selected)
    # Preserve independently researched issues; a machine-generated summary must not replace one.
    existing_issues=[]
    try:
        existing_issues=json.loads((DATA/'briefings.json').read_text(encoding='utf-8')).get('briefings',[])
    except (OSError,ValueError,AttributeError):
        pass
    editorial={x['week_start']:x for x in existing_issues if x.get('editorial') and x.get('week_start')}
    add_reports_to_editorial(editorial,briefings)
    briefings=list(editorial.values())+[x for x in briefings if x['week_start'] not in editorial]
    briefings.sort(key=lambda x:x['week_start'],reverse=True)
    briefings=[x for x in briefings if x['week_start']>='2026-09-07'][:7]
    payload={'updated_at':TODAY.isoformat(),'methodology':'All in-scope WNN and ANS news, NIA resources/news/blog, Breakthrough four nuclear innovation tabs, and Nuclear Energy-tagged NCEA publications; source_records.json retains every publication while visible news stories are event-level deduplicated with all publisher links. No quota; metadata and multi-label tags inferred from public descriptions. Historical discovery continues in 3,000-URL batches on recurring runs. Materiality scores affect ordering only.','articles':selected}
    (DATA/'source_records.json').write_text(json.dumps({
        'updated_at':TODAY.isoformat(),
        'methodology':'Every source-attributed dated publication from WNN, ANS, NIA, Breakthrough and NCEA, BEFORE event-level deduplication. Publisher-original text excerpts/URLs only, not full copyrighted articles.',
        'records':originals
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DATA/'articles.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DATA/'briefings.json').write_text(json.dumps({'generated_at':TODAY.isoformat(),'briefings':briefings},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Published:',len(originals),'original source records;',len(selected),'deduplicated public cards in',len(groups),'periods;',len(briefings),'weekly briefings.',flush=True)

if __name__=='__main__':
    main()
