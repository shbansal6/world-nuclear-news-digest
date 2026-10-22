#!/usr/bin/env python3
"""One-time offline normalization of NIA /index.php/ publication aliases.

No network requests, no new article ingestion, no changed classification.
Keep all *distinct* publisher publications and every original URL as an
alias. Repair weekly reports referencing equivalent old Drupal URLs.
"""
import json
from pathlib import Path
from refresh import canonicalize_source_records
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def read(file):
    return json.loads((DATA/file).read_text(encoding='utf-8'))

def unique(seq):
    recs=canonicalize_source_records(seq)
    return sorted(recs.values(),key=lambda x:(x.get('date',''),x.get('importance_score',0)),reverse=True)

def main():
    sources=read('source_records.json')
    display=read('articles.json')
    briefs=read('briefings.json')
    old_s=len(sources['records']);old_d=len(display['articles'])
    sources['records']=unique(sources['records'])
    display['articles']=unique(display['articles'])
    dropped_s=old_s-len(sources['records'])
    dropped_d=old_d-len(display['articles'])
    if (dropped_s,dropped_d)!=(5,5):
        raise RuntimeError('Unexpected alias collisions: '+str((dropped_s,dropped_d)))
    removed=0
    for b in briefs.get('briefings',[]):
        for section in b.get('sections',[]):
            old=len(section.get('items',[]))
            if not old:continue
            section['items']=unique(section['items'])
            delta=old-len(section['items'])
            removed+=delta
            if delta:
                b['article_count']=max(0,int(b.get('article_count',0))-delta)
                if section.get('category')=='New research reports':
                    b['report_count']=max(0,int(b.get('report_count',0))-delta)
    if removed!=5:
        raise RuntimeError('Expected 5 duplicate dated research items in briefings, got '+str(removed))
    originals={x['url'] for x in sources['records']}
    canonical={x['url'] for x in display['articles']}
    assert len(originals)==len(sources['records']),'Original source URL collision'
    assert len(canonical)==len(display['articles']),'Public URL collision'
    assert canonical<=originals,'Display articles missing original publisher provenance'
    assert len(display['articles'])>=6000,'Archive unexpectedly contracted'
    report_count=sum(x.get('kind')=='report' for x in display['articles'])
    print('Validated',len(sources['records']),'original works,',len(display['articles']),
          'display cards,',report_count,'research reports;',removed,'duplicate briefing items removed.')
    for name,obj in (('source_records.json',sources),('articles.json',display),('briefings.json',briefs)):
        (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
