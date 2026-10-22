"""Event-level WNN/ANS reconciliation. Preserve every original link.

Only news-versus-news pairs are eligible. Reports remain separate intellectual works.
Conservative gates stop unrelated Google/Amazon deals and lifecycle milestones merging.
"""
import datetime as dt
import re
from collections import defaultdict
from difflib import SequenceMatcher
from urllib.parse import urlsplit

NOISE=set("a an the for of to in on at and with from by as says said new nuclear energy power plant plants reactor reactors us uk international news update latest is are its".split())
CUSTOMERS={'aep','google','alphabet','amazon','aws','microsoft','meta','oracle','constellation','vistra','nextera','kairos','oklo','x-energy','terrapower','tva','opg','palisades','calvert','cliffs','duane','arnold','point','beach','vogtle','darlington'}
STAGES={
'ppa':re.compile(r'\b(ppa|power purchase|offtake|power supply agreement|power sales agreement)\b',re.I),
'restart':re.compile(r'\b(restart|reopening|reopen|recommission)\b',re.I),
'uprate':re.compile(r'\b(uprate|power boost|capacity increase)\b',re.I),
'licence':re.compile(r'\b(licen[cs]e|permit|regulatory approval)\b',re.I),
'construction':re.compile(r'\b(construction begins|first concrete|groundbreaking|breaks ground)\b',re.I),
'operation':re.compile(r'\b(commercial operation|first power|connected to grid|grid connected|criticality)\b',re.I)
}
def tokens(s):
    return set(w for w in re.findall(r'[a-z0-9]+',str(s or '').lower()) if w not in NOISE and len(w)>2)
def sim(a,b):
    a,b=tokens(a),tokens(b)
    return len(a&b)/len(a|b) if a and b else 0
def pct(a,b):
    a=re.sub(r'\s+',' ',str(a or '').lower()).strip()
    b=re.sub(r'\s+',' ',str(b or '').lower()).strip()
    return SequenceMatcher(None,a,b).ratio()
def important_names(a):
    t=tokens(' '.join((a.get('title',''),a.get('summary',''))))
    return t&CUSTOMERS
def figures(a):
    # MW/GW values and contract year durations are useful identity clues.
    title=' '.join((a.get('title',''),a.get('summary',''))).lower()
    values=set()
    for value,unit in re.findall(r'\b(\d[\d,.]*)\s*(mw|gw|gwe|mwe)\b',title):
        try:values.add(str(round(float(value.replace(',',''))*(1000 if unit.startswith('gw') else 1))))
        except ValueError:pass
    return values
def stages(a):
    s=(a.get('title','')+' '+a.get('summary',''))
    return {k for k,rx in STAGES.items() if rx.search(s)}
def same_event(a,b):
    if a.get('kind','news')!='news' or b.get('kind','news')!='news':return False
    if a.get('source')==b.get('source'):return False
    if {a.get('source'),b.get('source')}!={'World Nuclear News','ANS Nuclear Newswire'}:return False
    try:
        delta=abs((dt.date.fromisoformat(a['date'])-dt.date.fromisoformat(b['date'])).days)
    except (ValueError,KeyError):return False
    if delta>10:return False
    na,nb=important_names(a),important_names(b)
    # Conflicting material counterparties mean separate transactions.
    if na and nb and not na.intersection(nb):return False
    if {'google','amazon'}<=na|nb and ('google' in na)!=('google' in nb):return False
    if {'microsoft','meta'}<=na|nb and ('microsoft' in na)!=('microsoft' in nb):return False
    fa,fb=figures(a),figures(b)
    if fa and fb and not fa.intersection(fb) and len(fa)==1 and len(fb)==1:return False
    sa,sb=stages(a),stages(b)
    # Different milestones involving the same plant are distinct developments.
    if sa and sb and sa.isdisjoint(sb) and len(sa)==len(sb)==1:return False
    title=sim(a.get('title'),b.get('title'))
    body=sim(a.get('summary'),b.get('summary'))
    ordered=pct(a.get('title'),b.get('title'))
    return ((title>=.68 and body>=.22) or (title>=.48 and body>=.50) or (ordered>=.76 and body>=.20) or (delta<=2 and title>=.28 and body>=.24) or (delta<=2 and title>=.36 and body>=.12 and len(na&nb)>=2))
def reconcile(records):
    """Stable preference for WNN summary, ANS as secondary source link.
    Source duplicates are exposed via alternate_sources for audits, never discarded silently.
    """
    by_url={}
    for a in records:
        u=(a.get('url') or '').rstrip('/').lower()
        if not u:continue
        if u not in by_url or len(a.get('summary',''))>len(by_url[u].get('summary','')):
            by_url[u]=dict(a)
    source_records=sorted(by_url.values(),key=lambda a:(a.get('date',''),a.get('source')!='World Nuclear News'),reverse=True)
    by_day=defaultdict(list)
    result=[]
    for a in source_records:
        if a.get('kind','news')!='news':
            result.append(a);continue
        target=None
        d=dt.date.fromisoformat(a['date'])
        for offset in range(-10,11):
            for idx in by_day.get((d+dt.timedelta(days=offset)).isoformat(),[]):
                b=result[idx]
                if same_event(a,b):
                    target=idx;break
            if target is not None:break
        if target is None:
            by_day[a['date']].append(len(result))
            result.append(a)
        else:
            b=result[target]
            # WNN article is canonical; still display BOTH verified publisher links.
            if a.get('source')=='World Nuclear News':
                b,a=a,b
                result[target]=b
            aliases=b.setdefault('alternate_sources',[])
            aliases.append({'source':a.get('source','Other source'),'url':a['url'],'title':a.get('title','')})
            aliases.extend(a.get('alternate_sources',[]))
            b['entities']=sorted(set(b.get('entities',[])+a.get('entities',[])))
            b['technologies']=sorted(set(b.get('technologies',[])+a.get('technologies',[])))
            b['categories']=sorted(set(b.get('categories',[])+a.get('categories',[])))
            b['search_text']=' '.join([b.get('search_text',''),a.get('title',''),a.get('summary','')])
    for item in result:
        links={}
        for other in item.get('alternate_sources',[]):
            if other.get('url') and other['url'].rstrip('/').lower()!=item['url'].rstrip('/').lower():
                links[other['url'].rstrip('/').lower()]=other
        if links:item['alternate_sources']=list(links.values())
        elif 'alternate_sources' in item:del item['alternate_sources']
    return sorted(result,key=lambda x:(x.get('date',''),int(x.get('importance_score',0))),reverse=True)
