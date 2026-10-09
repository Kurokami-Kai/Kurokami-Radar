/* ================= Ofertas e Biblioteca: páginas próprias (radar/ofertas.html e biblioteca.html) num iframe =================
   As páginas pedem a ficha do jogo, o carrinho e a loja ao painel por window.KH (mesma origem). */
const FR={vale:{id:'frVale',url:'/kurokami/ofertas',sub:'dest'},bib:{id:'frBib',url:'/kurokami/biblioteca',sub:'bib'}};
function ajustaTopo(){const t=$('.topbar');if(t)document.documentElement.style.setProperty('--topoH',Math.max(0,Math.round(t.getBoundingClientRect().bottom))+'px');}
addEventListener('resize',ajustaTopo);
try{new ResizeObserver(ajustaTopo).observe($('.topbar'));new MutationObserver(ajustaTopo).observe(document.body,{childList:true});}catch(e){}
let ENTRANDO=true;   // velho só recarrega ao entrar na aba (nunca na cara de quem está usando)
function mostraFrame(t){const f=FR[t],el=$('#'+f.id);scrollTo(0,0);ajustaTopo();
  if(!el.getAttribute('src')||(f.velho&&ENTRANDO)){f.velho=false;el.hidden=true;$('#'+f.id+'Msg').hidden=false;
    el.onload=()=>{el.hidden=false;$('#'+f.id+'Msg').hidden=true;if(S.tab===t){focaFrame();buscaPend(f,el);}};el.src=f.url+'?t='+Date.now()+'#'+f.sub;}
  else{try{el.contentWindow.irSub(f.sub);}catch(e){}focaFrame();buscaPend(f,el);}}
function focaFrame(){const f=FR[S.tab];if(f)try{$('#'+f.id).contentWindow.focus();}catch(e){}}
/* Esc e "/" com o foco no painel (topo, abas): abrem (o Esc também fecha) a busca de Ofertas/Biblioteca; nas outras abas, o Esc leva à busca de Ofertas */
function buscaPend(f,el){if(!f.busca)return;f.busca=false;try{el.contentWindow.buscar();}catch(e){}}
addEventListener('keydown',e=>{if(e.key==='Escape'&&e.target.id==='pBusca'){e.target.blur();return;}
  if(!(e.key==='/'||e.key==='Escape')||!$('#modal').hidden||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)||e.target.isContentEditable)return;
  if(!FR[S.tab]){if(e.key!=='Escape'||!$('#buscaRes').hidden)return;e.preventDefault();
    if(S.tab==='lista'&&$('#pBusca')){$('#pBusca').focus();$('#pBusca').select();return;}   // na tabela com filtros, a busca é a dela
    FR.vale.busca=true;setTab('vale');return;}
  try{const w=$('#'+FR[S.tab].id).contentWindow;if(w.buscar){e.preventDefault();w.focus();w.buscar(e.key);}}catch(x){}});
let MOP={};   // como a ficha foi aberta: {vered, passo, pos} quando vem das páginas novas
window.KH={
  ficha(appid,op){abrirJogo(appid,op);},
  async carrinho(itens){let n=0,ja=0;
    for(const it of itens){if(CARR.some(c=>c.appid===it.appid)){ja++;continue;}
      if(it.mon){const r=await post('/api/extra',{appid:it.appid});if(!r||r.ok===false||r.erro){toast('Não consegui monitorar: '+((r&&r.erro)||'?'));continue;}}
      CARR.push({appid:it.appid,modo:'conta',loja:it.loja});n++;}
    if(n)await salvarCarr();
    const lj=[...new Set(itens.map(it=>(CARR.find(c=>c.appid===it.appid)||{}).loja).filter(Boolean))];
    toast(n?(n===1?'No carrinho':n+' no carrinho')+(lj.length===1?' · '+lj[0]:lj.length?' · '+lj.length+' lojas':'')+(ja?` · ${ja} já estava${ja>1?'m':''}`:''):'Já está no carrinho');},
  loja(a){open(storeUrl(a),'_blank','noopener');},
  aba(t){setTab(t);},
  instalarExt(){instalarExt();},
  extVersao(){return document.documentElement.dataset.kurokamiExt||'';},
  sub(aba,s){if(FR[aba])FR[aba].sub=s;},
  dlcsPromo(){FR.bib.sub='completar:capas';setTab('bib');}   // o Completar em Capas abre na ordem "Em promoção": as DLCs com desconto de cada jogo
};
