"""Publisher-provided XML sitemap discovery for complete Breakthrough archives.

Visible Nuclear Energy Innovation tabs contain only a subset of historical
publications. The official site index exposes article, blog and press maps.
Items from general blog/press maps still require a nuclear topic breadcrumb
on their own article page. XML loc URLs are discovery data, not publications.
"""
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from sources import parse_date

ROOT='https://thebreakthrough.org/sitemap.xml'

def locs(raw):
    try:doc=ET.fromstring(raw)
    except (ET.ParseError,TypeError):return []
    return [node.text.strip() for node in doc.findall('.//{*}loc') if node.text and node.text.strip().startswith('https://')]

def candidates(fetch):
    root=fetch(ROOT)
    if not root:
        print('WARNING Breakthrough official sitemap unavailable',flush=True)
        return {}
    maps={}
    for path in locs(root):
        if not urlparse(path).hostname in ('thebreakthrough.org','www.thebreakthrough.org'):continue
        if 'section-articles-' in path:maps[path]='articles'
        elif 'section-blog-' in path and 'blogLanding-' not in path:maps[path]='blog'
        elif 'section-press-' in path:maps[path]='press'
    found={}
    for uri,section in maps.items():
        raw=fetch(uri)
        if not raw:
            print('WARNING Breakthrough sitemap inaccessible: '+uri,flush=True)
            continue
        n=0
        for u in locs(raw):
            p=urlparse(u)
            if p.hostname not in ('thebreakthrough.org','www.thebreakthrough.org'):continue
            if section=='articles':
                if not p.path.startswith('/issues/nuclear-energy-innovation/'):continue
                # Older reports may sit in the articles sitemap too.
                kind,ptype,needs_breadcrumb='news','Article',False
            elif section=='blog':
                if not p.path.startswith('/blog/'):continue
                kind,ptype,needs_breadcrumb='report','Blog',True
            else:
                if not p.path.startswith('/press/'):continue
                kind,ptype,needs_breadcrumb='news','Press Release',True
            found[u.rstrip('/')]=(kind,ptype,needs_breadcrumb)
            n+=1
        print('Breakthrough sitemap '+section+': '+str(n)+' candidate links',flush=True)
    return found

def belongs_to_nuclear_innovation(page):
    """Require a nuclear topic breadcrumb before article title.

    The site-wide navigation mentions the topic on every page, so matching
    the entire document's text would wrongly ingest unrelated press/blog.
    """
    main=page.select_one('main,article')
    if not main:return False
    h=main.find('h1')
    if not h:return False
    text=main.get_text(' ',strip=True)
    title=h.get_text(' ',strip=True)
    pos=text.find(title)
    if pos<0:return False
    intro=text[max(0,pos-450):pos]
    return 'nuclear energy innovation' in intro.lower()
