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
'Policy & regulation':'Policy & international'
}
def entities_for(s):
    found=[]
    for marker,value in COMPANIES.items():
        if re.search(r'(?<![a-z])'+re.escape(marker)+r'(?![a-z])',s,re.I) and value not in found:
            found.append(value)
    return found

def enrich_record(a, article_excerpt=''):
    """Identify actual mentioned entities from article text. Do not store copyrighted body text."""
    title=a.get('title','')
    summary=a.get('summary','')
    description=a.get('description','')
    full=' '.join((title,summary,description,article_excerpt))
    existing=list(a.get('entities') or [])
    a['entities']=list(dict.fromkeys(existing+entities_for(full)))
    tech=list(a.get('technologies') or [])
    themes=list(a.get('categories') or [])
    for cat in TECHNOLOGIES:
        if COMPILED[cat].search(full) and cat not in tech:tech.append(cat)
    if not tech:tech.append('Traditional fission')
    for cat in CATEGORIES:
        if COMPILED[cat].search(full) and cat not in themes:themes.append(cat)
    old=OLD.get(a.get('category',''))
    if old and old not in themes:themes.append(old)
    # A story with named hyperscalers AND an actual power arrangement merits the customer tag.
    if (re.search(r'\b(google|amazon|microsoft|oracle|meta)\b',full,re.I)
        and re.search(r'\b(energy|electricity|power supply|purchase|offtake|ppa)\b',full,re.I)
        and 'Offtakes & customers' not in themes):
        themes.append('Offtakes & customers')
    a['technologies']=[x for x in TECHNOLOGIES if x in tech]
    a['categories']=[x for x in CATEGORIES if x in themes]
    # Only extracted entities and summary-level keywords retained, not copied article text.
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
