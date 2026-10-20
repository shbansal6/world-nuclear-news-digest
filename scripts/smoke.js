#!/usr/bin/env node
/* Minimal browser-runtime smoke test; catches blank dashboards and broken global search. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('app.js','utf8');
const news=JSON.parse(fs.readFileSync('data/articles.json','utf8'));
const briefing=JSON.parse(fs.readFileSync('data/briefings.json','utf8'));
const override=fs.existsSync('data/editorial_overrides.json')?JSON.parse(fs.readFileSync('data/editorial_overrides.json','utf8')):{};
const isNB=process.cwd().includes('neutron-bytes-digest');
const ids=['total','periods','briefcount','asof','yrfilter','monthfilter','techfilter','catfilter','yearnav','results','scope','archive-content','loadmore','weekly','archive','weekly-nav','weekly-main','q','sortfilter','expand','reset'];
const el={};for(const id of ids){el[id]={value:'all',innerHTML:'',textContent:'',hidden:false,listeners:{},addEventListener(type,cb){this.listeners[type]=cb},classList:{add(){},remove(){},toggle(){}},scrollIntoView(){}};}
const location={hash:''};
const document={body:{dataset:{source:isNB?'nb':'wnn'}},getElementById(id){assert(el[id],'Missing HTML element '+id);return el[id]},querySelectorAll(){return []},addEventListener(){}};
const files={'data/articles.json':news,'data/briefings.json':briefing,'data/editorial_overrides.json':override};
const fetch=async url=>{const path=url.split('?')[0];if(!(path in files))throw Error('Unresolved data file '+path);return {ok:true,json:async()=>files[path]}};
(async()=>{
 vm.runInNewContext(source,{document,window:{addEventListener(){}},location,fetch,console,URL,Date,Set,Map,Number,String,Array,RegExp,Boolean,Math,encodeURIComponent,decodeURIComponent});
 await new Promise(r=>setTimeout(r,150));
 assert(el.total.textContent&&!el.total.textContent.includes('—'),'Dashboard failed to initialize counters');
 assert((el['archive-content'].innerHTML.match(/news-card/g)||[]).length>0,'Archive cards did not render');
 assert(el.q.listeners.input,'Global search did not initialize');
 el.q.listeners.input({target:{value:'Amazon Constellation'}});
 assert(!el.results.textContent.startsWith('0 developments'),'Amazon–Constellation transaction not globally searchable');
 if(isNB)assert(el['archive-content'].innerHTML.includes('Amazon and Constellation sign'),'Neutron Bytes Oct 2 PPA not visible');
 el.q.listeners.input({target:{value:'Google Constellation'}});
 assert(!el.results.textContent.startsWith('0 developments'),'Google–Constellation deal not globally searchable');
 console.log('FRONTEND SMOKE TEST PASS:',el.total.textContent,'indexed developments; global search and news cards working');
})().catch(err=>{console.error(err.stack||err);process.exit(1)});
