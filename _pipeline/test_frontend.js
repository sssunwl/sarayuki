// Dependency-free checks of the actual page rendering functions with transient fixtures.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=require('path').resolve(__dirname,'..');
const snowPath=root+'/data/snow.json',photosPath=root+'/data/photos.json';
const originalSnow=fs.readFileSync(snowPath),originalPhotos=fs.existsSync(photosPath)?fs.readFileSync(photosPath):null;
const resorts=JSON.parse(fs.readFileSync(root+'/data/resorts.json'));
const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fake={generated:'2026-12-10T06:12:00+09:00',season:true,headline:{text:'過去 24 小時降雪最多：白馬 12 cm',stationCode:'48141'},stations:{'48141':{name:'白馬',alt:703,observedAt:'2026-12-10T06:00:00+09:00',snow:85,snow24h:12,temp:-5.2},'16217':{name:'倶知安',alt:176,observedAt:'2026-12-10T06:00:00+09:00',snow:50,snow24h:3,temp:null}}};
const photos={niseko:{thumb:'https://upload.wikimedia.org/fake.jpg',file:'https://commons.wikimedia.org/wiki/File:Fake.jpg',author:'Test Author',license:'CC BY-SA 4.0',licenseUrl:'https://creativecommons.org/licenses/by-sa/4.0/'}};
(async()=>{try{
 fs.writeFileSync(photosPath,JSON.stringify(photos));
 const home=fs.readFileSync(root+'/index.html','utf8');
 const homeScript=[...home.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
 for(const season of [true,false]){
  const fixture=season?fake:{generated:null,stations:{},headline:{text:'各觀測站目前還沒有積雪紀錄'},season:false};
  fs.writeFileSync(snowPath,JSON.stringify(fixture));
  const report={innerHTML:'雪季觀測從 12 月開始，各站目前還沒有積雪紀錄。'};
  await vm.runInNewContext(homeScript,{fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(root+'/'+url))}),document:{getElementById:()=>report},escapeHtml:esc,Intl,Date,console});
  if(season){assert.match(report.innerHTML,/積雪 cm/);assert.match(report.innerHTML,/12\/10 06:00/);assert.match(report.innerHTML,/resorts\/\?focus=happo/);assert.match(report.innerHTML,/—/);assert(report.innerHTML.indexOf('focus=happo')<report.innerHTML.indexOf('focus=niseko'))}
  else assert(!report.innerHTML.includes('snow-card'));
  const page=fs.readFileSync(root+'/resorts/index.html','utf8');
  const actual=page.slice(page.indexOf('const LEVELS='),page.indexOf('\nfunction render(){'));
  const context=vm.createContext({matchMedia:()=>({matches:false}),location:{search:''},URLSearchParams,Intl,Date,console});
  vm.runInContext(actual,context);
  context.fixtures={snow:fixture.stations,photos,resorts:resorts.resorts};
  const cards=vm.runInContext('snowStations=fixtures.snow;resortPhotos=fixtures.photos;fixtures.resorts.map(cardHtml).join("")',context);
  assert.match(cards,/Photo: Test Author \/ CC BY-SA 4.0 \/ Wikimedia Commons/);
  assert.match(cards,/Live Cam/);assert.match(cards,/纜車運行/);assert.match(cards,/data-live="appi"/);
  assert(!cards.includes('<iframe'));
  assert.strictEqual(cards.includes('❄ 積雪 85 cm'),season);
  const cortina=vm.runInContext('cardHtml(fixtures.resorts.find(r=>r.id==="cortina"))',context);
  assert(!cortina.includes('Live Cam'));assert(!cortina.includes('纜車運行'));assert(!cortina.includes('resort-photo'));
  // Exercise click-to-create, stream switching and close without a browser or network.
  const panel={hidden:true,innerHTML:'',replaceChildren(){this.innerHTML=''},parentElement:{querySelector:()=>({setAttribute(){}})}};
  let click;
  context.document={getElementById:id=>id==='cards'?{addEventListener:(name,handler)=>click=handler}:panel};
  vm.runInContext('allResorts=fixtures.resorts',context);
  const script=[...page.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
  vm.runInContext(script,context);
  const event=dataset=>({target:{closest:()=>({dataset,setAttribute(){}})}});
  click(event({live:'appi'}));assert.match(panel.innerHTML,/youtube-nocookie.com\/embed\/xrn4ifcQwj4/);
  click(event({stream:'appi',index:'1'}));assert.match(panel.innerHTML,/youtube-nocookie.com\/embed\/lhUjcOp4lBI/);
  click(event({live:'appi'}));assert(panel.hidden);assert(!panel.innerHTML.includes('iframe'));
  console.log('PASS frontend fixture:',season?'snow':'off-season','; photos, null links, lazy live, switch and close');
 }
 const report={innerHTML:'雪季觀測從 12 月開始，各站目前還沒有積雪紀錄。'};
 await vm.runInNewContext(homeScript,{fetch:async()=>{throw Error('offline')},document:{getElementById:()=>report},escapeHtml:esc,console});
 assert(!report.innerHTML.includes('snow-card'));console.log('PASS homepage network failure fallback');
}finally{fs.writeFileSync(snowPath,originalSnow);if(originalPhotos)fs.writeFileSync(photosPath,originalPhotos);else if(fs.existsSync(photosPath))fs.unlinkSync(photosPath)}})().catch(e=>{console.error(e);process.exitCode=1});
