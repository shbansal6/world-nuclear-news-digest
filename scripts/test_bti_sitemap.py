#!/usr/bin/env python3
"""Validate publisher sitemap discovery and nuclear-only breadcrumb screening."""
from bs4 import BeautifulSoup
from bti_sitemaps import candidates, belongs_to_nuclear_innovation, ROOT

BASE='https://thebreakthrough.org'
a=BASE+'/sitemaps-1-section-articles-1-sitemap-p1.xml'
b=BASE+'/sitemaps-1-section-blog-1-sitemap.xml'
p=BASE+'/sitemaps-1-section-press-1-sitemap.xml'
def xml(tag,items):
    return ('<?xml version="1.0"?><'+tag+' xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+
            ''.join('<'+('sitemap' if tag=='sitemapindex' else 'url')+'><loc>'+x+'</loc></'+
                    ('sitemap' if tag=='sitemapindex' else 'url')+'>' for x in items)+
            '</'+tag+'>').encode()
fixture={
  ROOT:xml('sitemapindex',[a,b,p]),
  a:xml('urlset',[BASE+'/issues/nuclear-energy-innovation/an-important-reactor-report',
                   BASE+'/issues/energy/unrelated-energy-article']),
  b:xml('urlset',[BASE+'/blog/nuclear-breadcrumb-item',BASE+'/blog/unrelated-food-research']),
  p:xml('urlset',[BASE+'/press/nuclear-breadcrumb-press'])
}
def test():
    records=candidates(lambda url:fixture.get(url,b''))
    assert len(records)==3,records
    assert records[BASE+'/issues/nuclear-energy-innovation/an-important-reactor-report']==('news','Article',False)
    assert records[BASE+'/blog/nuclear-breadcrumb-item']==('report','Blog',True)
    assert records[BASE+'/press/nuclear-breadcrumb-press']==('news','Press Release',True)
    nuclear=BeautifulSoup('<main><p>Nuclear Energy Innovation</p><h1>Press release headline</h1><p>Analysis</p></main>','html.parser')
    unrelated=BeautifulSoup('<nav>Nuclear Energy Innovation</nav><main><p>Food & Agriculture</p><h1>Press release headline</h1><p>Unrelated material</p></main>','html.parser')
    assert belongs_to_nuclear_innovation(nuclear)
    assert not belongs_to_nuclear_innovation(unrelated)
    print('BREAKTHROUGH SITEMAP COVERAGE REGRESSION PASS')
if __name__=='__main__':test()
