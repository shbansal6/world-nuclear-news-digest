"""Deterministic multi-label classification of source articles.
A story may receive zero or more commercial labels and technology labels.
These rules prefer precision for the archives, not fabricated claims.
"""
import re

TECHNOLOGIES=("Traditional fission","Advanced fission","Microreactors","Fusion")
CATEGORIES=("Restarts & uprates","Offtakes & customers","Construction & licensing",
"Fuel & supply chain","Capital & financing","Policy & international")
COMPANIES={
"constellation": "Constellation Energy","google": "Google","amazon": "Amazon","microsoft": "Microsoft",
"oracle": "Oracle","meta platforms":"Meta","meta": "Meta","nextera":"NextEra Energy",
"vistra":"Vistra","ge vernova":"GE Vernova","kairos":"Kairos Power","x-energy":"X-energy",
"tva":"Tennessee Valley Authority","tennessee valley authority":"Tennessee Valley Authority",
"nrc":"US Nuclear Regulatory Commission","doe":"US Department of Energy",
"terrapower":"TerraPower","oklo":"Oklo","nuscale":"NuScale","opg":"Ontario Power Generation",
"westinghouse":"Westinghouse","edf":"EDF","holtec":"Holtec","southern company":"Southern Company",
"georgia power":"Georgia Power","fortum":"Fortum","rolls-royce":"Rolls-Royce SMR",
"rosatom":"Rosatom","framatome":"Framatome","newcleo":"newcleo","orano":"Orano",
"urenco":"Urenco","centrus":"Centrus","bwxt":"BWXT","cez":"CEZ","čez":"CEZ",
"palisades":"Palisades","duane arnold":"Duane Arnold","point beach":"Point Beach",
"calvert cliffs":"Calvert Cliffs","vogtle":"Vogtle","hatch":"Hatch",
"bruce power":"Bruce Power","darlington":"Darlington","bwrx-300":"BWRX-300",
"xe-100":"Xe-100","arc clean technology":"ARC Clean Technology",
}
RX={
'Fusion':r'\b(fusion|tokamak|stellarator|plasma confinement)\b',
'Microreactors':r'\b(microreactor|micro-reactor|micro reactor|nuclear battery|evinci|e-vinci|project pele|janus program)\b',
'Advanced fission':r'\b(smr|small modular|advanced reactor|molten salt|fast reactor|bwrx.300|xe.100|kairos|x.energy|oklo|terrapower|nuscale|natrium|pebble.bed|htgr|gen.iv)\b',
'Traditional fission':r'\b(ap1000|epr|vver|candu|pressuri[sz]ed water|boiling water|traditional fission|large reactor|existing nuclear|nuclear plant|reactor fleet|vogtle|calvert cliffs|palisades|duane arnold)\b',
'Restarts & uprates':r'\b(restart|re-start|uprate|capacity increase|power increase|power boost|life extension|lifetime extension|extended operation|long.term operation|refurbish|reactor refurbishment|efficiency upgrade)\b',
'Offtakes & customers':r'\b(offtake|off.take|power purchase|ppa\b|energy supply agreement|electricity supply|electricity purchase|power supply agreement|subscribe to (?:a portion|output)|subscription to electricity|contracted power|supply power to|long.term power agreement)\b',
'Construction & licensing':r'\b(construction|commission|criticality|grid connection|grid.connected|licen[cs]|permit|siting|environmental impact|design certification|first power|first concrete|site preparation|reactor building)\b',
'Fuel & supply chain':r'\b(uranium|haleu|leu\b|enrich|centrifuge|triso|mox\b|fuel cycle|fuel fabrication|fuel supply|conversion plant|steam generator|reactor component|procurement|supply chain)\b',
'Capital & financing':r'\b(funding|financing|finance|fundraise|capital raise|ipo\b|investment|investor|joint venture|acquisition|debt package|loan guarantee|equity round|grant funding)\b',
'Policy & international':r'\b(policy|regulation|legislation|government|parliament|nuclear law|national strategy|bilateral|international partnership|iaea|nrc\b|ministry|minister|regulator)\b'
}
COMPILED={k:re.compile(v,re.I) for k,v in RX.items()}
OLD={
'Nuclear PPAs & offtake':'Offtakes & customers',
'Operations & restarts':'Restarts & uprates',
'New build & milestones':'Construction & licensing',
'SMRs & advanced reactors':'Construction & licensing',
'Uranium & fuel':'Fuel & supply chain',
'Corporate & financing':'Capital & financing',
'Policy & regulation':'Policy & international',
'Offtake & customers':'Offtakes & customers',
'Restarts & uprates':'Restarts & uprates',
'Construction & licensing':'Construction & licensing',
'Fuel & supply chain':'Fuel & supply chain',
'Capital & financing':'Capital & financing',
'Policy & international':'Policy & international'
}
def entities_for(s):
    found=[]
    for marker,value in COMPANIES.items():
        if re.search(r'(?<![a-z])'+re.escape(marker)+r'(?![a-z])',s,re.I) and value not in found:
            found.append(value)
    return found

def enrich_record(a, article_excerpt=''):
    """Tag the reported development, not every secondary subject named in the article.
    Recompute auto-tags on each run to correct older false-positive assignments.
    """
    title=a.get('title','')
    summary=a.get('summary','')
    description=a.get('description','')
    main=' '.join((title,summary,description))
    full=' '.join((main,article_excerpt))
    existing=list(a.get('entities') or [])
    a['entities']=list(dict.fromkeys(existing+entities_for(full)))

    # Primary technology is driven by article heading/summary, not examples used
    # in the body to compare SMRs with large-reactor uprates.
    original=a.get('category','')
    maintech=main+' '+original
    tech=[]
    if COMPILED['Fusion'].search(maintech):tech.append('Fusion')
    if COMPILED['Microreactors'].search(maintech):tech.append('Microreactors')
    if COMPILED['Advanced fission'].search(maintech) and not (tech==['Microreactors']):
        tech.append('Advanced fission')
    if (COMPILED['Traditional fission'].search(maintech) or not tech) and 'Traditional fission' not in tech:
        tech.append('Traditional fission')

    scored={}
    for label in CATEGORIES:
        # Distinguish article subject from background references.
        score=5*bool(COMPILED[label].search(title))+3*bool(COMPILED[label].search(summary))
        if COMPILED[label].search(article_excerpt):score+=1
        if OLD.get(original)==label:score+=5
        scored[label]=score
    if re.search(r'\b(google|amazon|microsoft|oracle|meta)\b',main,re.I) and re.search(r'\b(power purchase|power agreement|supply electricity|offtake|ppa|energy supply)\b',main,re.I):
        scored['Offtakes & customers']+=6
    # A plant uprate/customer agreement may describe "construction jobs" and
    # quote government aspirations; neither makes the article a new-build or
    # policy decision.
    if re.search(r'construction jobs?',full,re.I) and not re.search(r'\b(reactor construction|construction permit|nuclear construction|construction of|construction starts|first concrete|commissioning|grid connected)\b',main,re.I):
        scored['Construction & licensing']=min(scored['Construction & licensing'],2)
    if not re.search(r'\b(policy|regulat|licen[cs]|legisl|law|minister|iaea|nrc|government|parliament)\b',main,re.I) and OLD.get(original)!='Policy & international':
        scored['Policy & international']=min(scored['Policy & international'],2)
    if re.search(r'\b(uprate|capacity increase|efficiency upgrade)\b',article_excerpt,re.I) and re.search(r'\b(power purchase|offtake|customer|new nuclear capacity)\b',main,re.I):
        scored['Restarts & uprates']+=5
    if re.search(r'\b(investments? of|billion|million|funding|financing)\b',article_excerpt,re.I) and re.search(r'\b(customer|power purchase|ppa|890 mw|agreement)\b',main,re.I):
        scored['Capital & financing']+=2
    # Keep no more than three high-relevance commercial tags. Rank score is
    # for topic fit, not a quota on whether the article is in the archive.
    selected=sorted([(v,k) for k,v in scored.items() if v>=3],key=lambda vk:(-vk[0],CATEGORIES.index(vk[1])))[:3]
    a['technologies']=[t for t in TECHNOLOGIES if t in tech]
    a['categories']=[label for _,label in selected]
    a['search_text']=' '.join(a['entities']+[title,summary])
    a['importance_score']=importance(a,full)
    return a

def importance(a,full):
    """A display ranking, never an inclusion criterion; explicit 0..100 heuristic."""
    title=a.get('title','')
    score=10
    # Size and economic materiality
    if re.search(r'\b\d[\d,.]*\s*(?:gw|mw|gwe|mwe)\b',full,re.I):score+=13
    if re.search(r'(?:[$€£]\s?\d[\d,.]*\s*(?:billion|million|bn)\b|USD\s?\d[\d,.]*\s*(?:billion|million))',full,re.I):score+=12
    if re.search(r'\b(?:10|15|20|25|30)[-. ]year\b',full,re.I):score+=5
    # Reported development status; a plan should not score like operating plant.
    if re.search(r'\b(connected to the grid|achieves criticality|begins commercial operation|first concrete|operational|entered service)\b',title,re.I):score+=25
    elif re.search(r'\b(signed|agreed|contract|approved|licensed|issued|permit granted|power purchase agreement)\b',full,re.I):score+=18
    elif re.search(r'\b(plans|proposed|considering|aims|mou|non.binding|feasibility)\b',title,re.I):score+=7
    # Market relevance and strategic significance
    if re.search(r'\b(new nuclear capacity|uprate|restart|first of a kind|commercial reactor|fuel supply)\b',full,re.I):score+=20
    if re.search(r'\b(google|amazon|microsoft|oracle|meta|constellation|westinghouse|tva|nrc|doe)\b',full,re.I):score+=10
    if re.search(r'\b(first|milestone|largest|new|initial|agreement)\b',title,re.I):score+=5
    if re.search(r'\b(podcast|opinion|guest column|viewpoint)\b',title,re.I):score-=12
    return max(0,min(100,score))
