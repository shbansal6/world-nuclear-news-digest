"""Comprehensive, source-preserving collectors for nuclear intelligence.

Covers the publisher's dated archive from 2024 onward. The publisher's
topic/section membership is authoritative, rather than a keyword cutoff.
Publisher-originated research, comments, fact sheets, blog and analysis are
stored as reports; news and press releases as news. Both remain discoverable.
"""
import datetime as dt
import re
from collections import deque
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit
from bs4 import BeautifulSoup
from sources import article, ans_feed, ncea_reports, parse_date, verified_date, short

SOURCE_BTI='Breakthrough Institute'
SOURCE_NIA='Nuclear Innovation Alliance'
SOURCE_ANS='ANS Nuclear Newswire'
BASE_BTI='https://thebreakthrough.org'
BASE_NIA='https://nuclearinnovationalliance.org'
START=dt.date(2024,1,1)
BTE_SECTIONS={
    'articles':('news', 'Article'),
    'blog':('report', 'Blog'),
    'press':('news', 'Press Release'),
    'reports':('report', 'Report')
}

def canonical_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc.lower(),p.path.rstrip('/').replace('/index.php/','/').replace('/index.php',''),'', ''))

def description(page, heading=None):
    """Use actual publication deck, excerpt or description; never navigation text."""
    meta=page.select_one('meta[name="description"],meta[property="og:description"]')
    val=(meta.get('content') or '').strip() if meta else ''
    if len(val)>=55:return val
    if heading:
        sibling=heading.find_next(['h2','p'])
        if sibling:
            val=sibling.get_text(' ',strip=True)
            if len(val)>=55:return val
    main=page.select_one('main,article') or page
    candidates=[x.get_text(' ',strip=True) for x in main.find_all('p',limit=12)]
    return next((x for x in candidates if len(x)>=55 and not x.startswith('Subscribe')),val)

def bti_all(fetch, max_pages_per_tab=25):
    """Discover all four tabs independently, then fetch every distinct dated item.

    Additional page offsets are explored while results keep changing.
    Both canonical /issues/... and /blog/ or /press/ paths are allowed.
    """
    candidates={}
    for tab,(kind,doctype) in BTE_SECTIONS.items():
        seen=set()
        for page in range(max_pages_per_tab):
            query='?tab='+tab+('&page='+str(page) if page else '')
            raw=fetch(BASE_BTI+'/nuclear-energy-innovation'+query)
            if not raw:
                if page==0:print('Breakthrough '+tab+' listing unavailable',flush=True)
                break
            soup=BeautifulSoup(raw,'html.parser')
            matched=set()
            for a in soup.select('a[href]'):
                u=canonical_url(urljoin(BASE_BTI,a['href']))
                parsed=urlparse(u)
                if parsed.hostname not in ('thebreakthrough.org','www.thebreakthrough.org'):continue
                valid=(parsed.path.startswith('/issues/nuclear-energy-innovation/') or
                       (tab=='blog' and parsed.path.startswith('/blog/')) or
                       (tab=='press' and parsed.path.startswith('/press/')))
                if not valid:continue
                matched.add(u)
                old=candidates.get(u)
                # Explicit report/blog classification takes precedence if same URL is
                # exposed under multiple tab views.
                if old is None or kind=='report':candidates[u]=(kind,doctype)
            new=matched-seen
            seen.update(matched)
            if not matched or (page and not new):break
            if page==max_pages_per_tab-1:
                print('WARNING Breakthrough '+tab+' page bound reached; review backfill',flush=True)
        print('Breakthrough '+tab+': '+str(len(seen))+' unique linked publications',flush=True)
    out=[]
    for u,(kind,doctype) in candidates.items():
        raw=fetch(u)
        if not raw:continue
        page=BeautifulSoup(raw,'html.parser')
        h=page.find('h1')
        if not h:continue
        title=h.get_text(' ',strip=True)
        date=verified_date(page)
        if not date:
            # Date beneath the title, not a report date mentioned in the article.
            excerpt=h.find_parent(['article','main']) or page
            text=excerpt.get_text(' ',strip=True)
            pos=text.find(title)
            date=parse_date(text[pos+len(title):pos+len(title)+350]) if pos>=0 else None
        desc=description(page,h)
        a=article(title,desc,u,date,SOURCE_BTI,kind,desc)
        if a:
            a['publication_type']=doctype
            out.append(a)
    print('Breakthrough: '+str(len(out))+' verified nuclear publication records',flush=True)
    return out

def listing_pages(fetch,base,max_pages=150):
    """Crawl Drupal publication listing until pagination ends (not first four pages)."""
    results=[]
    seen_urls=set()
    seen_page_signatures=set()
    for page in range(max_pages):
        raw=fetch(base+('?page='+str(page) if page else ''))
        if not raw:
            if page==0:print('WARNING missing listing '+base,flush=True)
            break
        soup=BeautifulSoup(raw,'html.parser')
        # Only actual content cards count, never the navigation/footer.
        headings=soup.select('main h2, main h3, .view-content h2, .view-content h3')
        if not headings:headings=soup.select('h2,h3')
        signature=tuple(h.get_text(' ',strip=True) for h in headings[:8])
        if not signature or signature in seen_page_signatures:break
        seen_page_signatures.add(signature)
        results.append((page,soup,headings))
        # The last actual page often lacks "next"; some Drupal themes hide
        # it in the HTML, so a short next-page probe is still permitted.
        if page==max_pages-1:print('WARNING pagination safety bound '+base,flush=True)
    return results

def nia_cards(fetch,base,resource=False):
    """Collect NIA cards of every resource type, plus news and blog.

    Page title & date come from its own card, not from neighboring cards.
    """
    out=[]
    for page,soup,headings in listing_pages(fetch,base):
        for h in headings:
            a=h.find('a',href=True)
            if not a:
                a=h.find_parent('a',href=True)
            if not a:continue
            url=canonical_url(urljoin(BASE_NIA,a['href']))
            p=urlparse(url)
            if p.hostname not in ('nuclearinnovationalliance.org','www.nuclearinnovationalliance.org'):continue
            if p.path in ('/resources','/news','/index.php/resources','/index.php/news'):continue
            title=h.get_text(' ',strip=True)
            if len(title)<16:continue
            # Drupal output frequently uses a views-row wrapper.
            card=h.find_parent(class_=re.compile(r'views-row|views-field|node',re.I))
            if not card:
                card=h.parent
                for _ in range(3):
                    if card and len(card.get_text(' ',strip=True))<50:card=card.parent
            excerpt=card.get_text(' ',strip=True) if card else ''
            # Don't consume the following card's date or description.
            d=parse_date(excerpt[:450])
            preview=next((p.get_text(' ',strip=True) for p in card.select('p') if len(p.get_text(' ',strip=True))>=55), '') if card else ''
            typename=''
            if resource:
                for label in ('NIA Public Comments','Fact Sheets','Letters/Testimonies','Supporting Materials',
                              'Deployment Maps','Reports','Videos'):
                    if re.search(r'\b'+re.escape(label)+r'\b',excerpt,re.I):
                        typename=label;break
                typename=typename or 'Resource'
                kind='report'
            else:
                typename='Press Release' if re.search(r'\bPress Release\b',excerpt,re.I) else 'Blog'
                kind='news' if typename=='Press Release' else 'report'
            # Detail page is authoritative for complete title, date, summary.
            detail=fetch(url)
            if detail:
                pagehtml=BeautifulSoup(detail,'html.parser')
                h1=pagehtml.find('h1')
                if h1 and len(h1.get_text(' ',strip=True))>=16:title=h1.get_text(' ',strip=True)
                d=verified_date(pagehtml) or d
                desc=description(pagehtml,h1)
            else:desc=''
            if len(desc)<55:desc=preview
            rec=article(title,desc,url,d,SOURCE_NIA,kind,desc)
            if rec:
                rec['publication_type']=typename
                out.append(rec)
    unique={a['url']:a for a in out}
    print('NIA '+('resources' if resource else 'news/blog')+': '+str(len(unique))+' dated source records',flush=True)
    return list(unique.values())

def collect_all_sources(fetch):
    out=[]
    for name,fn in (
        ('ANS',ans_feed),
        ('NIA resources',lambda f: nia_cards(f,BASE_NIA+'/resources',True)),
        ('NIA news and blog',lambda f: nia_cards(f,BASE_NIA+'/news',False)),
        ('Breakthrough all 4 tabs',bti_all),
        ('NCEA Nuclear Energy',ncea_reports)):
        try:
            data=fn(fetch)
            print(name+': '+str(len(data))+' dated publications',flush=True)
            out.extend(data)
        except Exception as error:
            print('WARNING '+name+' collector failed: '+str(error)[:200],flush=True)
    return list({r['url']:r for r in out}.values())
