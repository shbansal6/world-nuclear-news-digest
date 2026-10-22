#!/usr/bin/env python3
"""Offline regressions for four-tab Breakthrough and all-type NIA collectors."""
from comprehensive_sources import bti_all, nia_cards, canonical_url
from dedupe import same_event, reconcile

BTI='https://thebreakthrough.org'
NIA='https://nuclearinnovationalliance.org'

def page(title,desc,date):
    return ('<html><head><meta name="description" content="'+desc+'"></head>'
            '<body><main><h1>'+title+'</h1><time datetime="'+date+'"></time>'
            '<p>'+desc+'</p></main></body></html>').encode()

long='This publication examines nuclear sector developments, their implications for deployment and regulatory choices, and key questions for stakeholders.'
tabs={'articles':'/issues/nuclear-energy-innovation/article-a','blog':'/blog/nuclear-blog-a','press':'/press/nuclear-press-a','reports':'/issues/nuclear-energy-innovation/report-a'}
fixtures={}
for tab,url in tabs.items():
    fixtures[BTI+'/nuclear-energy-innovation?tab='+tab]=('<main><a href="'+url+'">Test document</a></main>').encode()
    fixtures[BTI+url]=page('Nuclear '+tab+' publication',long,'2026-10-15')
for kind,name,slug in [('NIA Public Comments','Nuclear regulatory comments','comment-a'),
                       ('Fact Sheets','Nuclear deployment factsheet','fact-a'),
                       ('Reports','Nuclear financing report','report-a')]:
    pass
fixtures[NIA+'/resources']=(''.join(
 '<div class="views-row"><h2><a href="/'+slug+'">'+name+'</a></h2><time>October 14th, 2026</time><p>'+long+'</p><p>'+kind+'</p></div>'
 for kind,name,slug in [('NIA Public Comments','Nuclear regulatory comments','comment-a'),
                        ('Fact Sheets','Nuclear deployment factsheet','fact-a'),
                        ('Reports','Nuclear financing report','report-a')])).encode()
for slug in ('comment-a','fact-a','report-a'):
    fixtures[NIA+'/'+slug]=page('Nuclear '+slug+' source material',long,'2026-10-14')
fixtures[NIA+'/news']='<div class="views-row"><h2><a href="/news-a">Nuclear energy press release</a></h2><p>October 12th, 2026</p><p>'+long+'</p><p>Press Release</p></div>'.encode()
fixtures[NIA+'/news-a']=page('Nuclear energy press release',long,'2026-10-12')

def fetch(url):return fixtures.get(url,b'')

def test():
    out=bti_all(fetch,max_pages_per_tab=2)
    assert len(out)==4,[(x['title'],x.get('publication_type')) for x in out]
    actual={x['publication_type']:x['kind'] for x in out}
    assert actual=={'Article':'news','Blog':'report','Press Release':'news','Report':'report'},actual
    nia=nia_cards(fetch,NIA+'/resources',True)
    assert len(nia)==3,[(x['title'],x.get('publication_type')) for x in nia]
    assert {x['publication_type'] for x in nia}=={'NIA Public Comments','Fact Sheets','Reports'}
    for x in nia:assert x['kind']=='report'
    news=nia_cards(fetch,NIA+'/news',False)
    assert len(news)==1 and news[0]['kind']=='news',news
    assert canonical_url(NIA+'/index%2Ephp/report-a')==NIA+'/report-a'

    # Same factual event across news publishers has one display card but
    # research on that same subject must remain independent.
    w={'date':'2026-10-20','title':'TVA Clinch River 300 MW reactor construction permit approved',
       'summary':'The NRC issued TVA a construction permit for a 300 MW SMR reactor at Clinch River in Tennessee.',
       'source':'World Nuclear News','url':'https://world-nuclear-news.org/articles/tva-permit','kind':'news'}
    bt={'date':'2026-10-20','title':'NRC approves TVA Clinch River 300 MW construction permit',
        'summary':'The NRC approved a construction permit for TVA to build a 300 MW SMR reactor at Clinch River in Tennessee.',
        'source':'Breakthrough Institute','url':'https://thebreakthrough.org/press/tva-permit','kind':'news'}
    assert same_event(w,bt)
    display=reconcile([w,bt])
    assert len(display)==1 and len(display[0]['alternate_sources'])==1
    report=dict(bt,url='https://thebreakthrough.org/issues/nuclear-energy-innovation/tva-analysis',kind='report')
    assert len(reconcile([w,bt,report]))==2
    print('COMPREHENSIVE SOURCE REGRESSIONS PASSED')

if __name__=='__main__':test()
