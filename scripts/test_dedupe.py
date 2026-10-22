#!/usr/bin/env python3
"""Source matching regression cases: distinguish event identity from repeated articles."""
from dedupe import same_event, reconcile
def rec(title,description,source,date='2026-10-19',kind='news'):
    return {'title':title,'summary':description,'source':source,'date':date,'kind':kind,
            'url':'https://www.world-nuclear-news.org/articles/'+str(abs(hash(title))) if source=='World Nuclear News' else 'https://www.ans.org/news/'+str(abs(hash(title)))}
def test():
    w='World Nuclear News';a='ANS Nuclear Newswire'
    d1=rec('AEP, Amazon and X-energy planning 12-SMR plant',
        'AEP, Amazon and X-energy announced plans for a small modular reactor project in Indiana and feasibility work.',w)
    d2=rec('Amazon, AEP, X-energy explore SMR feasibility in Indiana',
        'Amazon and AEP are exploring a feasibility study with X-energy to build small nuclear reactors in Indiana.',a)
    assert same_event(d1,d2),'Equivalent same-day headline must reconcile'
    assert len(reconcile([d1,d2]))==1,'One physical event should create one public card'
    unrelated=rec('Google and Constellation sign nuclear power purchase agreement',
        'Google agrees to buy electricity from Constellation nuclear plants under a twenty-year agreement.',a)
    amazon=rec('Amazon and Constellation sign nuclear power purchase agreement',
        'Amazon agrees to buy electricity from Constellation nuclear plants under a twenty-year agreement.',w)
    assert not same_event(unrelated,amazon),'Distinct nuclear customers must never merge'
    operating=rec('Station achieves first criticality and begins operation',
        'The reactor generated first power at the facility and entered service.',a)
    approval=rec('Station obtains construction permit',
        'The same nuclear facility receives a construction license and regulatory permission.',w)
    assert not same_event(operating,approval),'Approval and operation are separate milestones'
    r=rec(d1['title'],d1['summary'],'Nuclear Innovation Alliance',kind='report')
    assert not same_event(r,d2),'Independent source research is not repeated news coverage'
    once=reconcile([d1,d2])[0]
    assert len(once['alternate_sources'])==1 and once['source']==w,'Canonical WNN summary keeps ANS citation'
    twice=reconcile([once,d2])[0]
    assert len(twice['alternate_sources'])==1,'Recurring refresh must not duplicate alternate citations'
    print('Deduplication regression suite passed.')
if __name__=='__main__':test()
