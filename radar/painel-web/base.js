/* ================= abertura ================= */
/* a logo se desenha ao abrir: uma vez por sessão do navegador; clique ou tecla pula */
(function(){const el=document.getElementById('abertura');if(!el)return;let fim=false;
const sai=()=>{if(fim)return;fim=true;el.classList.add('sai');setTimeout(()=>el.remove(),600);};
try{if(sessionStorage.getItem('kr:abertura')||matchMedia('(prefers-reduced-motion:reduce)').matches){el.remove();return;}sessionStorage.setItem('kr:abertura','1');}catch(e){}
el.addEventListener('click',sai);
addEventListener('keydown',e=>{if(fim)return;e.stopImmediatePropagation();e.preventDefault();sai();},true);
setTimeout(sai,2400);})();
/* ================= helpers ================= */
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const brl=c=>c==null?'—':(c===0?'Grátis':'R$ '+(c/100).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}));
const brl0=c=>'R$ '+Math.round((c||0)/100).toLocaleString('pt-BR');
const fmtK=n=>n>=1000?(n/1000).toFixed(n>=10000?0:1).replace('.',',')+' mil':String(n);
const fmtN=n=>(n||0).toLocaleString('pt-BR');
const fmtUnix=t=>t?new Date(t*1000).toLocaleDateString('pt-BR',{day:'2-digit',month:'short',year:'numeric'}).replace('.',''):'';
const fmtISO=t=>t?new Date(t).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'';
const hue=id=>((id*2654435761)>>>0)%360;
const storeUrl=id=>`https://store.steampowered.com/app/${id}/`;
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('on');clearTimeout(toast.t);toast.t=setTimeout(()=>t.classList.remove('on'),3500);}
const ls={get(k,d){try{const v=localStorage.getItem('kr:'+k);return v==null?d:JSON.parse(v);}catch(e){return d;}},set(k,v){try{localStorage.setItem('kr:'+k,JSON.stringify(v));}catch(e){}}};
async function api(p){const r=await fetch(p);if(!r.ok){const e=(await r.json().catch(()=>({}))).erro||r.status;toast('Erro: '+e);throw new Error(e);}return r.json();}
async function post(p,d){try{Object.values(FR).forEach(f=>{f.velho=true;});}catch(e){}let r;try{r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d||{})});}
  catch(e){toast('O Hunter não respondeu. Ele está aberto na bandeja?');return {ok:false,erro:String(e)};}
  const j=await r.json().catch(()=>({ok:false,erro:'resposta inválida'}));if(!r.ok||j.ok===false){toast('Não deu certo: '+(j.erro||r.status));if(j.ok===undefined)j.ok=false;}return j;}
function ph(name,id,small){return `<span class="ph${small?' sm':''}" style="--h:${hue(id)}"><span>${esc(name)}</span></span>`;}
function art(id,name,url,o={}){
  const src=url||o.alt;const alt=url&&o.alt?` data-alt="${esc(o.alt)}"`:'';
  const inner=src?`<img src="${esc(src)}" alt="" loading="lazy" decoding="async" data-ph="${esc(name)}" data-id="${id}"${alt}>`:ph(name,id,o.small);
  return `<span class="art${o.v?' vert':''}"${o.style?` style="${o.style}"`:''}>${inner}</span>`;
}
document.addEventListener('error',e=>{const im=e.target;if(im.tagName!=='IMG'||im.dataset.ph==null)return;
  if(im.dataset.alt){const a=im.dataset.alt;im.removeAttribute('data-alt');im.parentElement.classList.remove('vert');im.src=a;return;}
  im.outerHTML=ph(im.dataset.ph,+im.dataset.id);},true);
function revClass(p,n){return !n?'rv-non':(p>=95?'rv-top':p>=70?'rv-pos':(p>=40?'rv-mix':'rv-neg'));}

/* ================= estado ================= */
let L=[], IDX=new Map(), RES={};
const S=Object.assign({tab:'vale',pview:'tabela'},ls.get('s',{}),{q:'',shown:50});
const save=()=>{const {q,shown,...r}=S;ls.set('s',r);};

/* ================= blocos ================= */
function priceBlock(o,lg){
  if(o.preco==null)return `<span class="pb tba${lg?' lg':''}"><span class="prs"><span class="f">${o.em_breve?'Em breve':'Sem preço'}</span></span></span>`;
  if(o.corte>0)return `<span class="pb${lg?' lg':''}"><span class="pct">-${o.corte}%</span><span class="prs tnum"><span class="o">${brl(o.cheio)}</span><span class="f">${brl(o.preco)}</span></span></span>`;
  return `<span class="pb full${lg?' lg':''}"><span class="prs tnum"><span class="f">${brl(o.preco)}</span></span></span>`;
}
const ksBarata=o=>o.keyshop!=null&&o.preco!=null&&o.keyshop<o.preco*0.6;
const SELO_SVG='<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="29" fill="#000" stroke="#000" stroke-width="5"/><path d="M22 38a11 11 0 0 1 20 0" stroke="#ff4757" stroke-width="4" fill="none"/><path d="M32 32 50 16" stroke="#ff4757" stroke-width="5"/><circle cx="32" cy="32" r="7" fill="#ff4757"/></svg>';
function seloBadge(o){return o.selo?`<span class="selo" title="${esc('Selo Kurokami: '+(o.selo_motivo||'o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade'))}">${SELO_SVG}SELO KUROKAMI</span>`:'';}
function mesAno(iso){if(!iso)return '';const d=new Date(iso);return String(d.getMonth()+1).padStart(2,'0')+'/'+d.getFullYear();}
function pisoRefTxt(r){return r?`${brl(r.preco)}${r.corte?' a -'+r.corte+'%':''} (${mesAno(r.quando_preco||r.quando)})`:'';}
function pisoPill(o){const p=recPill(o);if(p)return p;const r=o.piso_ref;
  return o.corte>0&&r&&o.tipo_oferta!=='selo'?`<span class="pp pp-ref">menor: ${esc(pisoRefTxt(r))}</span>`:'';}
function precoComPiso(o){const p=pisoPill(o);return p?`<span class="ppwrap">${priceBlock(o)}${p}</span>`:priceBlock(o);}
function fimTxt(t){if(!t)return '';const h=(t*1000-Date.now())/36e5;if(h<=0||h>72)return '';return h<1?'termina em minutos':h<24?`termina em ${Math.round(h)}h`:`termina em ${Math.round(h/24)}d`;}
function flags(o){
  const f=[];
  const ft=fimTxt(o.fim);if(ft)f.push(`<span class="flag">⏳ ${ft}</span>`);
  if(o.mudo)f.push('<span class="flag own">🔕 sem alertas</span>');
  if(o.novo)f.push('<span class="pill-novo">NOVO</span>');
  if(o.selo)f.push(seloBadge(o));
  if(o.vale)f.push('<span class="flag alert">🔔 Avisa</span>');
  if(o.modo==='completo')f.push('<span class="flag cmp">Modo completo</span>');
  if(o.base_tenho)f.push('<span class="flag own">Você tem o jogo base</span>');
  if(o.bundles)f.push(`<span class="flag bun">Em ${o.bundles} bundle${o.bundles>1?'s':''}</span>`);
  if(o.extra)f.push('<span class="flag">Adicionado por você</span>');
  if(ksBarata(o))f.push(`<span class="flag ks">Keyshop ${brl(o.keyshop)}</span>`);
  return f.join('');
}
function revText(o){return o.rcount?`<span class="${revClass(o.rpos,o.rcount)}">${esc(o.rotulo||o.rpos+'%')}</span> <span style="color:var(--dim)">(${fmtK(o.rcount)})</span>`:'<span class="rv-non">Sem análises</span>';}
/* o carrinho é só da Steam: jogo cujo melhor preço está em outra loja ganha um botão que abre a página dela, no lugar do + */
function lojaExt(id){const o=IDX.get(id);return o&&o.loja&&o.loja!=='Steam'&&o.preco!=null?o:null;}
async function abrirNaLoja(id,loja){
  const x=IDX.get(id),u0=x&&x.loja===loja&&/^https:\/\//.test(x.url||'')?x.url:null;
  if(u0){open(u0,'_blank','noopener');return;}
  const w=open('about:blank','_blank');if(w)try{w.opener=null;}catch(e){}   // abre já, no clique; o endereço vem em seguida
  let u=null;try{const m=await api('/api/jogo?appid='+id);const l=(m.lojas||[]).find(l=>l.loja===loja&&/^https:\/\//.test(l.url||''));u=l&&l.url;}catch(e){}
  if(u&&w){w.location=u;return;}
  if(w)w.close();toast('Sem link direto da '+loja+': a ficha mostra as lojas.');abrirJogo(id);}
function cartBtn(id,mon){const x=lojaExt(id);
  if(x)return `<span class="cartbtn ext" role="button" tabindex="0" data-lojaext="${id}" data-loja="${esc(x.loja)}" title="Abrir na ${esc(x.loja)} (o carrinho é só da Steam)">↗</span>`;
  const on=CARR.some(c=>c.appid===id);return `<span class="cartbtn${on?' on':''}" role="button" tabindex="0" data-cart="${id}"${mon?' data-mon="1"':''} title="${on?'Tirar do carrinho':mon?'Pôr no carrinho (e monitorar)':'Pôr no carrinho'}">${on?'✓':'+'}</span>`;}
const abre=o=>o.steam_inteira?`data-open="${o.appid}"`:`data-open="${o.appid}" data-hv="${o.appid}"`;   // Steam inteira: ficha sem o cartão de passar o mouse
function capCard(o){return `<a class="cap" href="#" ${abre(o)}>${art(o.appid,o.nome,o.capa)}
  <div class="meta"><div class="nm">${esc(o.nome)}</div><div class="row"><span class="rvs">${revText(o)}</span><span style="display:flex;gap:5px;align-items:center">${cartBtn(o.appid,o.steam_inteira)}${precoComPiso(o)}</span></div></div></a>`;}

/* ================= hover ================= */
const HV=$('#hv');let hvT=null,hvEl=null;
function hvHTML(id){const o=IDX.get(+id);if(!o)return '';
  const tags=[];if(o.vale)tags.push('<span class="g">Avisa</span>');if(o.selo)tags.push('<span class="g">Selo Kurokami</span>');
  if(o.base_tenho)tags.push('<span>Você tem o jogo base</span>');if(o.modo==='completo')tags.push('<span class="v">Modo completo</span>');
  if(o.bundles)tags.push(`<span class="v">Em ${o.bundles} bundle(s)</span>`);
  return `<h4>${esc(o.nome)}</h4><div class="rel">${o.lancamento?'Lançamento: '+fmtUnix(o.lancamento):'Na sua lista de desejos'}</div>
    ${art(o.appid,o.nome,o.capa)}
    <div class="revl">Análises: ${o.rcount?`<b class="${revClass(o.rpos,o.rcount)}">${esc(o.rotulo)}</b> · ${o.rpos}% de ${fmtN(o.rcount)}`:'<b>sem análises</b>'}</div>
    <div class="kv tnum">${o.preco!=null?`<span>Melhor preço (${esc(o.loja)})</span><b>${brl(o.preco)}</b>`:''}
      ${o.corte>0?`<span>Preço cheio</span><b>${brl(o.cheio)}</b>`:''}
      ${o.volta_texto?`<span>Costuma voltar</span><b>${esc(o.volta_texto)}</b>`:''}${o.tipo_oferta?`<span>Preço</span><b>${TIPO_NOME[o.tipo_oferta]}</b>`:''}<span>Menor de sempre</span><b>${brl(o.piso)}</b>
      ${o.keyshop!=null?`<span>Keyshop (GG.deals)</span><b>${brl(o.keyshop)}</b>`:''}
</div>
    ${tags.length?`<div class="tags">${tags.join('')}</div>`:''}<div class="note">Clique para ver histórico, lojas e caminhos de compra</div>`;}
document.addEventListener('mouseover',e=>{const el=e.target.closest('[data-hv]');if(el===hvEl)return;clearTimeout(hvT);HV.classList.remove('on');hvEl=el;if(!el)return;
  hvT=setTimeout(()=>{const h=hvHTML(el.dataset.hv);if(!h)return;HV.innerHTML=h;const r=el.getBoundingClientRect(),w=310,hh=HV.offsetHeight;
    let x=r.right+10;if(x+w>innerWidth-8)x=r.left-w-10;if(x<8)x=Math.min(innerWidth-w-8,Math.max(8,r.left));let y=r.top;if(y+hh>innerHeight-8)y=innerHeight-hh-8;if(y<8)y=8;
    HV.style.left=x+'px';HV.style.top=y+'px';HV.classList.add('on');},260);});
addEventListener('scroll',()=>{clearTimeout(hvT);HV.classList.remove('on');hvEl=null;},{passive:true});
let CARR=[];
async function salvarCarr(){const r=await post('/api/carrinho',{itens:CARR});$('#carrN').textContent=CARR.length?'('+CARR.length+')':'';
  return r;}
async function alternarCarr(id,forcar,mon){const i=CARR.findIndex(c=>c.appid===id);
  if(i>=0&&forcar!==true){CARR.splice(i,1);toast('Saiu do carrinho');}
  else if(i<0){if(mon){const r=await post('/api/extra',{appid:id});if(!r||r.ok===false||r.erro){toast('Não consegui monitorar: '+((r&&r.erro)||'?'));return;}}CARR.push({appid:id,modo:'conta',loja:'Steam'});}
  await salvarCarr();if(i<0)toast((mon?'No carrinho e monitorado (entra na lista na próxima checagem)':'No carrinho da Steam'));$$(`[data-cart="${id}"]`).forEach(el=>{const on=CARR.some(c=>c.appid===id);el.classList.toggle('on',on);el.textContent=on?'✓':'+';});
  if(S.tab==='carr')renderCarr();if(S.tab==='lista')renderLista();}
document.addEventListener('click',e=>{const c=e.target.closest('[data-lojaext]');if(!c)return;e.preventDefault();e.stopPropagation();abrirNaLoja(+c.dataset.lojaext,c.dataset.loja);},true);
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('span[role="button"][tabindex]')){e.preventDefault();e.target.click();}});   // os botões em <span> também respondem ao teclado
document.addEventListener('click',e=>{const c=e.target.closest('[data-cart]');if(!c)return;e.preventDefault();e.stopPropagation();alternarCarr(+c.dataset.cart,false,c.dataset.mon==='1');},true);
async function alternarBundle(id){const i=CARR.findIndex(c=>c.bundle===id);if(i>=0){CARR.splice(i,1);toast('Bundle saiu do carrinho');}else{CARR.push({bundle:id,modo:'conta'});toast('Bundle no carrinho');}
  await salvarCarr();$$(`[data-cartb="${id}"]`).forEach(el=>{const on=CARR.some(c=>c.bundle===id);el.classList.toggle('on',on);el.textContent=on?'✓':'+';});
  if(S.tab==='carr')renderCarr();}
document.addEventListener('click',e=>{const c=e.target.closest('[data-cartb]');if(!c)return;e.preventDefault();e.stopPropagation();alternarBundle(+c.dataset.cartb);},true);
document.addEventListener('click',e=>{const o=e.target.closest('[data-open]');if(!o)return;e.preventDefault();HV.classList.remove('on');abrirJogo(+o.dataset.open);});

/* ================= abas ================= */
function setTab(t){ENTRANDO=S.tab!==t;S.tab=t;save();document.body.dataset.tab=t;document.body.classList.toggle('emframe',!!FR[t]);try{history.replaceState(null,'','#'+t);}catch(e){}$$('.nav [data-tabs]').forEach(b=>b.setAttribute('aria-current',b.dataset.tabs.split(' ').includes(t)?'page':'false'));
  ['vale','lista','bib','carr','notif','cfg'].forEach(x=>$('#tab-'+x).hidden=x!==t);render();}
$('#logoHome').addEventListener('click',e=>{e.preventDefault();setTab('vale');window.scrollTo({top:0,behavior:'smooth'});});
$('.nav').addEventListener('click',e=>{if(e.target.closest('[data-dlcpromo]')){KH.dlcsPromo();e.target.blur();return;}
  const b=e.target.closest('[data-tab]');if(!b)return;
  if(b.dataset.ir==='promo')aplicarP(P_PADRAO);
  if(b.dataset.sub&&FR[b.dataset.tab])FR[b.dataset.tab].sub=b.dataset.sub;
  setTab(b.dataset.tab);if(b.closest('.ddm'))b.blur();});

/* ================= tipos de recorde (Configurações e a tabela de Promoções) ================= */
let VIT=null;   // /api/vitrine: só para o "N na vitrine" do topo
const TIPO_NOME={selo:'Selo Kurokami',novo:'Novo recorde',igual:'Igual ao recorde','24m':'Menor em 2 anos'};
const TIPO_DESC={selo:'O menor preço anterior foi há 1,5 ano ou mais, ou o preço caiu pela metade',novo:'Nunca esteve tão barato',
  igual:'No mesmo preço do menor já registrado','24m':'No menor preço dos últimos 2 anos'};
const TIPO_COR={selo:'#ff4757',novo:'#d63031',igual:'#8a1520','24m':'#5c5c5c'};
