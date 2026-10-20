/* One UI for the World Nuclear News and Neutron Bytes research libraries.
 * Every search runs across the FULL in-memory archive before pagination, not DOM cards.
 */
(()=>{'use strict';
const $=id=>document.getElementById(id), site=document.body.dataset.source==='nb'?'nb':'wnn';
const TECHNOLOGIES=['Traditional fission','Advanced fission','Microreactors','Fusion'];
const THEMES=['Restarts & uprates','Offtakes & customers','Construction & licensing','Fuel & supply chain','Capital & financing','Policy & international'];
const MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
const state={year:'all',month:'all',tech:'all',theme:'all',q:'',sort:'recent',expanded:false,visible:100};
let articles=[],briefings=[],metadata={};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function validUrl(u){try{const p=new URL(u);return p.protocol==='https:'||p.protocol==='http:'?p.href:''}catch{return ''}}
function dateLabel(d){if(!/^\d{4}-\d\d-\d\d$/.test(d))return d||'';return new Date(d+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'})}
function periodKey(a){let d=a.date||'';return d.slice(0,4)<='2024'?d.slice(0,4)+'-Q'+Math.ceil(Number(d.slice(5,7))/3):d.slice(0,7)}
function periodName(k){if(k.includes('-Q'))return 'Quarter '+k.slice(-1);return MONTHS[Number(k.slice(5,7))-1]||k}
function compact(s,n=325){s=String(s||'').replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n).replace(/\s+\S*$/,'')+'…':s}
const any=(s,re)=>re.test(s);
function tagsFor(a){
 const content=[a.title,a.summary,a.category,(a.entities||[]).join(' '),(a.search_text||''),a.description||''].join(' ').toLowerCase();
 const title=(a.title||'').toLowerCase(), initial=(a.category||'').toLowerCase();
 const tech=[],tags=[];
 const put=(list,v)=>{if(!list.includes(v))list.push(v)};
 if(any(content,/\b(?:fusion|tokamak|stellarator|plasma confinement|inertial confinement)\b/))put(tech,'Fusion');
 if(any(content,/\b(?:microreactor|micro-reactor|micro reactor|nuclear battery|kilopower|project pele|e-vinci|evinci|dome test|dome demonstration)\b/))put(tech,'Microreactors');
 if(any(content,/\b(?:smr|small modular|advanced reactor|molten.salt|fast neutron|fast reactor|bwrx|bwrx-300|xe-100|nuscale|kairos|x-energy|oklo|newcleo|fourth.generation|gen iv|htgr|pebble.bed|natrium|terrapower)\b/)&&!tech.includes('Microreactors'))put(tech,'Advanced fission');
 if(any(content,/\b(?:ap1000|apr1400|epr2?|vver|pwr|bwr|candu|phwr|fleet|large reactor|traditional|conventional|existing nuclear|nuclear station|nuclear plant|existing unit|reactor units|vogtle|calvert cliffs|palisades|three mile island)\b/)||(tech.length===0&&!any(content,/\bfusion\b/)))put(tech,'Traditional fission');
 const original={
 'offtake & customers':'Offtakes & customers','nuclear ppas & offtake':'Offtakes & customers',
 'operations & restarts':'Restarts & uprates','restarts & uprates':'Restarts & uprates',
 'new build & milestones':'Construction & licensing','construction & licensing':'Construction & licensing',
 'smrs & advanced reactors':'Construction & licensing','uranium & fuel':'Fuel & supply chain',
 'fuel & supply chain':'Fuel & supply chain','corporate & financing':'Capital & financing',
 'capital & financing':'Capital & financing','policy & regulation':'Policy & international',
 'policy & international':'Policy & international'
 };
 if(original[initial])put(tags,original[initial]);
 if(any(content,/\b(?:offtake|off.take|power purchase agreement|power purchase|ppa\b|customer agreement|energy supply agreement|electricity supply agreement|long.term supply agreement|power supply agreement|contracted power|buy nuclear power|supply electricity|subscribe to.*electricity|subscription to.*power)\b/) || (any(content,/\b(?:google|amazon|microsoft|meta|oracle|data cent(?:re|er)|hyperscaler)\b/) && any(content,/\b(?:energy|electricity|power|offtake|capacity purchase|power supply)\b/)))
   put(tags,'Offtakes & customers');
 if(any(content,/\b(?:restart|re.start|recommission|uprate|power boost|capacity increase|capacity expansion|efficiency upgrade|operating life|life extension|life.time extension|refurbish|reactor refurbishment|extended operations?|long.term operation)\b/))
   put(tags,'Restarts & uprates');
 if(any(content,/\b(?:licen[cs]|construction|building works|commission|criticality|grid connection|connected to the grid|permit|site approval|environmental impact|design certification|construction milestone|first power|first concrete|first nuclear)\b/))
   put(tags,'Construction & licensing');
 if(any(content,/\b(?:uranium|fuel cycle|haleu|leu\b|enrich|centrifuge|triso|mox\b|fuel supply|fuel fabrication|fuel production|mining|supply chain|components|steam generator|supplier|equipment procurement|conversion plant)\b/))
   put(tags,'Fuel & supply chain');
 if(any(content,/\b(?:funding|financing|finance|fundraise|capital raise|equity|investment|investor|invests|venture funding|ipo\b|acquisition|loan guarantee|grant funding|debt package|secured .*million|secured .*\$|loan facility|joint venture)\b/))
   put(tags,'Capital & financing');
 if(any(content,/\b(?:policy|regulation|regulatory|legislation|parliament|government|nrc\b|iaea\b|minister|national programme|international partnership|bilateral agreement|country agreement|nuclear law|national strategy)\b/))
   put(tags,'Policy & international');
 return {technologies:tech,categories:tags};
}
function hydrate(x){
 const n=Object.assign({},x);
 n.date=String(n.date||'').slice(0,10);
 n.title=String(n.title||'');
 n.summary=String(n.summary||'');
 n.entities=Array.isArray(n.entities)?n.entities:[];
 const inferred=tagsFor(n);
 n.technologies=[...new Set([...(Array.isArray(n.technologies)?n.technologies:[]),...inferred.technologies])].filter(t=>TECHNOLOGIES.includes(t));
 n.categories=[...new Set([...(Array.isArray(n.categories)?n.categories:[]),...inferred.categories])].filter(t=>THEMES.includes(t));
 n.searchblob=[n.title,n.summary,n.category,n.search_text,...n.entities,...n.technologies,...n.categories,n.url].join(' ').toLowerCase();
 return n;
}
function sourceLinks(a){
 const list=[{url:a.url,label:site==='nb'?'Neutron Bytes':'World Nuclear News'},...(Array.isArray(a.links)?a.links:[])];
 const seen=new Set();let result=[];
 list.forEach(l=>{const u=validUrl(l.url);if(!u||seen.has(u))return;seen.add(u);if(result.length<4)result.push('<a target="_blank" rel="noopener noreferrer" href="'+esc(u)+'">'+esc(l.label||'Original linked source')+' <span>↗</span></a>')});
 return '<div class="sources">'+result.join('')+'</div>';
}
function tagChips(a){return '<div class="taggroup">'+a.technologies.map(t=>'<button type="button" class="tagchip tech" data-tech="'+esc(t)+'">'+esc(t)+'</button>').join('')+a.categories.map(t=>'<button type="button" class="tagchip" data-cat="'+esc(t)+'">'+esc(t)+'</button>').join('')+'</div>';}
function card(a){return '<article class="news-card'+(state.expanded?' expanded':'')+'"><div class="story-top"><span class="story-category">'+esc(a.categories[0]||a.category||'Nuclear developments')+'</span><span class="story-date">'+dateLabel(a.date)+'</span></div><h4>'+esc(a.title)+'</h4>'+tagChips(a)+'<div class="story-teaser">'+esc(compact(a.summary,250))+'</div><div class="story-full">'+esc(a.summary)+'</div>'+sourceLinks(a)+'</article>'}
function filtered(){const result=articles.filter(a=>(state.year==='all'||a.date.slice(0,4)===state.year)&&(state.month==='all'||a.date.slice(5,7)===state.month)&&(state.tech==='all'||a.technologies.includes(state.tech))&&(state.theme==='all'||a.categories.includes(state.theme))&&(!state.q||state.q.split(/\s+/).every(term=>a.searchblob.includes(term)))));if(state.sort==='significant')result.sort((a,b)=>(Number(b.importance_score)||0)-(Number(a.importance_score)||0)||b.date.localeCompare(a.date));return result;}
function renderList(){
 const found=filtered(), subset=found.slice(0,state.visible), years=new Map();
 subset.forEach(a=>{const y=a.date.slice(0,4);if(!years.has(y))years.set(y,new Map());const k=periodKey(a);if(!years.get(y).has(k))years.get(y).set(k,[]);years.get(y).get(k).push(a)});
 $('results').textContent=found.length.toLocaleString()+' developments';
 $('scope').textContent=state.q?'Search across all '+articles.length.toLocaleString()+' indexed developments (all source records and company metadata).':'Showing '+Math.min(found.length,state.visible).toLocaleString()+' of '+found.length.toLocaleString()+' matching developments. Global search spans all years; use a filter to narrow the view.';
 let html='';
 if(!found.length){$('archive-content').innerHTML='<div class="empty">No matching news. Try a broader search or clear your filters.</div>';$('loadmore').hidden=true;return;}
 for(const [year,periods] of years){
  const allYear=found.filter(a=>a.date.startsWith(year));
  html+='<section class="archive-year" id="year-'+esc(year)+'"><div class="year-header"><div class="year-number">'+year+'</div><div class="year-info"><div class="year-kicker">'+(Number(year)<=2024?'QUARTERLY COVERAGE':'MONTHLY COVERAGE')+'</div><h3>Source-linked nuclear developments · technology and transaction tags</h3></div><div class="year-count">'+allYear.length+'<span>matching developments</span></div></div><div class="period-wrap">';
  for(const [key,arr] of periods){
   const allPeriod=found.filter(a=>periodKey(a)===key);
   html+='<section class="period" id="period-'+key+'"><div class="period-heading"><div class="period-tick"></div><div><div class="period-name">'+esc(periodName(key))+'</div><div class="period-sub">'+allPeriod.length+' matching developments</div></div></div><div class="period-cards">'+arr.map(card).join('')+'</div></section>';
  } html+='</div></section>';
 }
 $('archive-content').innerHTML=html;
 $('loadmore').hidden=found.length<=state.visible;
 $('loadmore').textContent='Show more developments ('+(found.length-state.visible)+' remaining)';
}
function updateMonth(){
 const sel=$('monthfilter'), y=state.year,enabled=(y==='2025'||y==='2026');
 sel.disabled=!enabled;
 if(!enabled)state.month='all';
 const present=[...new Set(articles.filter(a=>a.date.startsWith(y+'-')).map(a=>a.date.slice(5,7)))].sort((a,b)=>b.localeCompare(a));
 sel.innerHTML='<option value="all">All months</option>'+present.map(m=>'<option value="'+m+'">'+MONTHS[Number(m)-1]+'</option>').join('');
 sel.value=state.month;
}
function renderNav(){
 const years=[...new Set(articles.map(a=>a.date.slice(0,4)))].sort().reverse();
 $('yrfilter').innerHTML='<option value="all">All years</option>'+years.map(y=>'<option value="'+y+'">'+y+'</option>').join('');
 $('techfilter').innerHTML='<option value="all">All technologies</option>'+TECHNOLOGIES.map(t=>'<option>'+esc(t)+'</option>').join('');
 $('catfilter').innerHTML='<option value="all">All categories</option>'+THEMES.map(t=>'<option>'+esc(t)+'</option>').join('');
 $('yearnav').innerHTML=years.map(y=>'<a href="#year-'+y+'" data-year="'+y+'"><b>'+y+'</b><span>'+articles.filter(a=>a.date.startsWith(y)).length+'</span></a>').join('');
 $('total').textContent=articles.length.toLocaleString();
 $('periods').textContent=new Set(articles.map(periodKey)).size;
 $('briefcount').textContent=briefings.length;
 $('asof').textContent='Archive updated '+(metadata.updated_at||'—');
 updateMonth();
}
function makeBriefing(st,ed){
 const items=articles.filter(a=>a.date>=st&&a.date<=ed);
 if(!items.length)return null;
 const grouped={};items.forEach(a=>{const key=a.categories[0]||'Other developments';(grouped[key]||(grouped[key]=[])).push(a)});
 return {week_start:st,week_end:ed,generated_at:'Source-record roundup',article_count:items.length,title:'Nuclear developments — week of '+dateLabel(st),overview:'Source-linked developments for the completed week, organized by sector. Refer to the original articles for the full reporting.',sections:Object.entries(grouped).map(([category,items])=>({category,takeaway:items.length+' developments indexed in '+category.toLowerCase()+'.',items}))};
}
function generateRecentWeeks(){
 const list=[];let d=new Date('2026-10-12T12:00:00Z');
 for(let i=0;i<6;i++){const end=new Date(d);end.setUTCDate(d.getUTCDate()+6);const b=makeBriefing(d.toISOString().slice(0,10),end.toISOString().slice(0,10));if(b)list.push(b);d.setUTCDate(d.getUTCDate()-7)}
 return list;
}
function loadBriefings(input){
 const output=(Array.isArray(input)?input:input?.briefings||[]).filter(b=>b.week_start>='2026-09-07');
 const seen=new Set(output.map(b=>b.week_start));
 // Preview issues for uncovered recent weeks, using only source records, no invented reporting.
 generateRecentWeeks().forEach(b=>{if(!seen.has(b.week_start))output.push(b)});
 return output.sort((a,b)=>b.week_start.localeCompare(a.week_start)).slice(0,7);
}
function weekly(start){
 $('archive').classList.add('hidden');$('weekly').classList.add('active');
 const chosen=briefings.find(b=>b.week_start===start)||briefings[0];
 $('weekly-nav').innerHTML=briefings.map(b=>'<a class="'+(b===chosen?'active':'')+'" href="#weekly-'+esc(b.week_start)+'">'+dateLabel(b.week_start)+' <span style="float:right">'+Number(b.article_count||0)+'</span></a>').join('');
 if(!chosen){$('weekly-main').innerHTML='<div class="empty">No weekly editions are indexed yet.</div>';return}
 let h='<div class="weekly-note"><div class="section-eyebrow" style="margin:0">WEEK OF '+dateLabel(chosen.week_start).toUpperCase()+' — '+dateLabel(chosen.week_end).toUpperCase()+'</div><h3>'+esc(chosen.title)+'</h3><p>'+esc(chosen.overview||'Source-linked nuclear market news for the week.')+'</p><div class="notice">'+(chosen.editorial?'Researched briefing':'Automated source-linked roundup')+' · '+Number(chosen.article_count||0)+' news items</div>';
 for(const s of (chosen.sections||[])){h+='<section class="weekly-sector"><h4>'+esc(s.category)+'</h4><p class="explanation">'+esc(s.takeaway||'')+'</p>';
  for(const item of (s.items||[])){const a=hydrate(item);h+='<div class="weekly-event"><h5>'+esc(a.title)+'</h5><p>'+esc(a.summary)+'</p>'+tagChips(a)+sourceLinks(a)+'</div>'}
  h+='</section>';
 } h+='</div>';$('weekly-main').innerHTML=h;
}
function updateView(){
 const hash=decodeURIComponent(location.hash||'#archive');
 if(hash.startsWith('#weekly'))weekly(hash.replace('#weekly-',''));else{$('weekly').classList.remove('active');$('archive').classList.remove('hidden');if(hash.startsWith('#year-')){const y=hash.slice(6);if($('yrfilter').value!==y&&/^\d{4}$/.test(y)){state.year=y;$('yrfilter').value=y;updateMonth();}}renderList();}
}
function resetView(){state.year='all';state.month='all';state.tech='all';state.theme='all';state.q='';state.sort='recent';state.visible=100;$('sortfilter').value='recent';['yrfilter','monthfilter','techfilter','catfilter'].forEach(id=>$(id).value='all');$('q').value='';updateMonth();renderList();}
function initEvents(){
 ['yrfilter','monthfilter','techfilter','catfilter'].forEach((id)=>$(id).addEventListener('change',e=>{const key={yrfilter:'year',monthfilter:'month',techfilter:'tech',catfilter:'theme'}[id];state[key]=e.target.value;state.visible=100;if(key==='year')updateMonth();if(location.hash.startsWith('#weekly'))location.hash='#archive';renderList();}));
 $('sortfilter').addEventListener('change',e=>{state.sort=e.target.value;state.visible=100;renderList()});
 $('q').addEventListener('input',e=>{state.q=e.target.value.trim().toLowerCase();state.visible=100;if(location.hash.startsWith('#weekly'))location.hash='#archive';renderList()});
 $('expand').addEventListener('click',()=>{state.expanded=!state.expanded;$('expand').textContent=state.expanded?'Show summaries':'Show detail';document.querySelectorAll('.news-card').forEach(c=>c.classList.toggle('expanded',state.expanded))});
 $('reset').addEventListener('click',e=>{e.preventDefault();resetView();location.hash='#archive'});
 $('loadmore').addEventListener('click',()=>{state.visible+=100;renderList()});
 document.addEventListener('click',e=>{const tag=e.target.closest('.tagchip');if(!tag)return;const type=tag.hasAttribute('data-tech')?'tech':'theme';state[type]=tag.getAttribute(type==='tech'?'data-tech':'data-cat');$(type==='tech'?'techfilter':'catfilter').value=state[type];state.visible=100;location.hash='#archive';renderList();document.getElementById('archive').scrollIntoView({behavior:'smooth'})});
 window.addEventListener('hashchange',updateView);
}
async function start(){
 const fetchJson=async path=>{const r=await fetch(path+'?v='+Date.now(),{cache:'no-cache'});if(!r.ok)throw Error('Missing '+path+': '+r.status);return r.json()};
 try{
  const [news,weeklyData]=await Promise.all([fetchJson('data/articles.json'),fetchJson('data/briefings.json').catch(()=>({briefings:[]}))]);
  metadata=Array.isArray(news)?{}:news;
  articles=(Array.isArray(news)?news:news.articles||[]).filter(a=>a.date&&a.title&&a.url).map(hydrate).sort((a,b)=>b.date.localeCompare(a.date)||a.title.localeCompare(b.title));
  briefings=loadBriefings(weeklyData);
  renderNav();initEvents();updateView();
 }catch(e){$('archive-content').innerHTML='<div class="empty">The archive could not load. Please refresh the page. '+esc(e.message)+'</div>';console.error(e);}
} start();
})();