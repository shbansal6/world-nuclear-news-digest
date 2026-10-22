"""Additional nuclear intelligence sources. Public pages/RSS only; no API keys.
Fail closed on missing dates or descriptions. Research entries are distinct documents.
"""
import datetime as dt
import email.utils
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from taxonomy import enrich_record

MONTHS={m.lower():i for i,m in enumerate(("January","February","March","April","May","June","July","August","September","October","November","December"),1)}
DATE_RX=re.compile(r'\b('+'|'.join(MONTHS)+r')\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b',re.I)
START=dt.date(2024,1,1)
def parse_date(value):
    if not value:return None
    s=str(value).strip()
    try:return dt.date.fromisoformat(s[:10])
    except ValueError:pass
    m=DATE_RX.search(s)
    if m:
        try:return dt.date(int(m.group(3)),MONTHS[m.group(1).lower()],int(m.group(2)))
        except ValueError:return None
    try:return email.utils.parsedate_to_datetime(s).date()
    except (ValueError,TypeError,IndexError):return None

def short(s,n=420):
    s=re.sub(r'\s+',' ',str(s or '')).strip()
    return s if len(s)<=n else s[:n].rsplit(' ',1)[0].strip()+'…'

def verified_date(soup, fallback=''):
    for sel,attr in [('meta[property="article:published_time"]','content'),('meta[name="datePublished"]','content'),('meta[itemprop="datePublished"]','content'),('time[datetime]','datetime')]:
        node=soup.select_one(sel)
        if node and (d:=parse_date(node.get(attr))):return d
    for sc in soup.select('script[type="application/ld+json"]'):
        try:
            import json
            j=json.loads(sc.string or '{}')
            seq=j if isinstance(j,list) else [j]
            for item in seq:
                if isinstance(item,dict) and (d:=parse_date(item.get('datePublished'))):return d
        except (ValueError,TypeError):pass
    return parse_date(fallback)

def article(title,summary,url,date,source,kind,body=''):
    if not (date and START<=date<=dt.date.today() and 15<len(title)<=240 and len(summary)>=55 and url.startswith('https://')):return None
    a={'date':date.isoformat(),'title':short(title,230),'summary':short(summary),'category':'Research & analysis' if kind=='report' else 'Nuclear developments','url':url.split('#')[0],'source':source,'kind':kind,'links':[]}
    return enrich_record(a,short(body,2500))

def ans_feed(fetch):
    """Official ANS RSS has reliable titles, descriptions, published dates and source URLs."""
    xml=fetch('https://www.ans.org/news/feed/')
    if not xml:return []
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    out=[]
    for item in root.findall('.//item'):
        title=short(item.findtext('title') or '',240)
        link=(item.findtext('link') or '').strip()
        parsed=urlparse(link)
        if parsed.hostname not in ('ans.org','www.ans.org') or not parsed.path.startswith('/news/'):continue
        date=parse_date(item.findtext('pubDate') or item.findtext('{http://purl.org/dc/elements/1.1/}date'))
        if not date:continue
        summary=BeautifulSoup(item.findtext('description') or '', 'html.parser').get_text(' ',strip=True)
        if len(summary)<55:
            raw=fetch(link)
            if raw:
                soup=BeautifulSoup(raw,'html.parser')
                desc=soup.select_one('meta[name="description"]')
                if desc:summary=desc.get('content','')
        a=article(title,summary,link,date,'ANS Nuclear Newswire','news')
        if a:out.append(a)
    return out

def nia_reports(fetch, pages=4):
    """Read the NIA resources library; include only resources explicitly marked Reports."""
    base='https://nuclearinnovationalliance.org'
    out=[]
    for page in range(pages):
        raw=fetch(base+'/resources?page='+str(page))
        if not raw:continue
        soup=BeautifulSoup(raw,'html.parser')
        for h in soup.select('h2,h3'):
            anchor=h.find('a',href=True)
            if not anchor:continue
            title=h.get_text(' ',strip=True)
            url=urljoin(base,anchor['href'])
            if urlparse(url).hostname not in ('nuclearinnovationalliance.org','www.nuclearinnovationalliance.org'):continue
            # Extract only the card's own content, stopping at the next report heading.
            chunks=[]
            for el in h.next_elements:
                if getattr(el,'name',None) in ('h2','h3'):break
                if getattr(el,'name',None) in ('p','time','span','div') and el.find_parent(['h2','h3']) is None:
                    t=el.get_text(' ',strip=True)
                    if t and t not in chunks and len(t)<1200:chunks.append(t)
                if len(chunks)>25:break
            body=' '.join(chunks)
            if not re.search(r'\bReports\b',body):continue
            date=parse_date(body)
            # Publication card date is required, rather than guessing from crawl date.
            if not date:continue
            snippets=[x for x in chunks if len(x)>95 and 'Nuclear Innovation Alliance' not in x[:30]]
            summary=snippets[0] if snippets else ''
            a=article(title,summary,url,date,'Nuclear Innovation Alliance','report',body)
            if a:out.append(a)
    return list({a['url']:a for a in out}.values())

def breakthrough_reports(fetch,max_pages=40):
    """Collect published nuclear research/analysis, not the organization's press releases."""
    base='https://thebreakthrough.org'
    raw=fetch(base+'/nuclear-energy-innovation?tab=reports') or fetch(base+'/nuclear-energy-innovation')
    if not raw:return []
    soup=BeautifulSoup(raw,'html.parser')
    urls=[]
    for a in soup.find_all('a',href=True):
        u=urljoin(base,a['href']).split('?')[0]
        if urlparse(u).netloc in ('thebreakthrough.org','www.thebreakthrough.org') and '/issues/nuclear-energy-innovation/' in urlparse(u).path and u not in urls:
            urls.append(u)
    out=[]
    for u in urls[:max_pages]:
        doc=fetch(u)
        if not doc:continue
        page=BeautifulSoup(doc,'html.parser')
        h=page.find('h1')
        if not h:continue
        title=h.get_text(' ',strip=True)
        date=verified_date(page)
        if not date:
            # Breakthrough places a date adjacent to the title.
            near=h.find_parent(['article','main']) or page
            date=parse_date(near.get_text(' ',strip=True)[:700])
        meta=page.select_one('meta[name="description"]')
        description=(meta.get('content') or '') if meta else ''
        if len(description)<55:
            p=h.find_next('p')
            description=p.get_text(' ',strip=True) if p else ''
        a=article(title,description,u,date,'Breakthrough Institute','report',description)
        if a:out.append(a)
    return out

def collect(fetch):
    outputs=[]
    for name,fn in [('ANS',ans_feed),('NIA',nia_reports),('Breakthrough',breakthrough_reports)]:
        try:
            items=fn(fetch)
            print(name+': '+str(len(items))+' verified new-source records',flush=True)
            outputs.extend(items)
        except Exception as exc:
            # Do not destroy saved records on transient source/network errors.
            print(name+' source unavailable: '+str(exc)[:180],flush=True)
    # NCEA Energy Policy Research Library requires its actual URL. Never crawl a guessed library.
    return list({a['url']:a for a in outputs}.values())
