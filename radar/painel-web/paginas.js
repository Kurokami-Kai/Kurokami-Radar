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
/* Teclado do painel. 1–4 trocam de seção (Ofertas, Biblioteca, Configurações, Carrinho); ⇧1–⇧3, de página dentro dela;
   "/" e Esc abrem a busca; uma letra solta abre a busca já com ela. Com o foco num iframe, a página repassa 1–4 por KH.irSecao. */
const SECOES=['vale','bib','cfg','carr'];
const SUBS_SECAO={vale:['dest','promo','lista'],bib:['bib','completar'],cfg:['cfg','notif']};
const secaoDe=t=>t==='lista'?'vale':t==='notif'?'cfg':t;
function irSecao(n){const t=SECOES[n-1];if(!t||S.tab===t)return;setTab(t);}
function irPagina(n){const sec=secaoDe(S.tab),s=(SUBS_SECAO[sec]||[])[n-1];if(!s)return;if(FR[sec]){FR[sec].sub=s;setTab(sec);}else setTab(s);}
function buscaPend(f,el){if(!f.busca)return;f.busca=false;try{el.contentWindow.buscar();}catch(e){}}
addEventListener('keydown',e=>{if(e.key==='Escape'&&(e.target.id==='pBusca'||e.target.id==='busca')){e.target.blur();return;}
  if(!$('#modal').hidden||e.ctrlKey||e.altKey||e.metaKey||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)||e.target.isContentEditable)return;
  const d=/^(?:Digit|Numpad)([1-9])$/.exec(/^Numpad/.test(e.code||'')&&!/^\d$/.test(e.key)?'':e.code||'');
  if(d){e.preventDefault();e.shiftKey?irPagina(+d[1]):irSecao(+d[1]);return;}
  const letra=e.key.length===1&&/\p{L}/u.test(e.key);
  if(!(e.key==='/'||e.key==='Escape'||letra))return;
  const digita=letra?e.key:'';
  if(!FR[S.tab]){
    if(S.tab==='carr'&&$('#busca')&&e.key!=='Escape'){e.preventDefault();const b=$('#busca');b.focus();if(digita){b.value=digita;b.dispatchEvent(new Event('input'));}return;}
    if(S.tab==='lista'&&$('#pBusca')){e.preventDefault();const b=$('#pBusca');b.focus();if(digita){b.value=digita;b.dispatchEvent(new Event('input',{bubbles:true}));}else b.select();return;}   // na tabela com filtros, a busca é a dela
    if(e.key!=='Escape'||!$('#buscaRes').hidden)return;   // Configurações e Notificações: letra solta não abre nada; o Esc leva à busca de Ofertas
    e.preventDefault();FR.vale.busca=true;setTab('vale');return;}
  try{const w=$('#'+FR[S.tab].id).contentWindow;if(w.buscar){e.preventDefault();w.focus();w.buscar(e.key);}}catch(x){}});
let MOP={};   // como a ficha foi aberta: {vered, passo, pos} quando vem das páginas novas
window.KH={
  ficha(appid,op){abrirJogo(appid,op);},
  async carrinho(itens,fora){let n=0,ja=0;
    for(const it of itens){if(CARR.some(c=>c.appid===it.appid)){ja++;continue;}
      if(it.mon){const r=await post('/api/extra',{appid:it.appid});if(!r||r.ok===false||r.erro){toast('Não consegui monitorar: '+((r&&r.erro)||'?'));continue;}}
      CARR.push({appid:it.appid,modo:'conta',loja:'Steam'});n++;}
    if(n)await salvarCarr();
    toast(n?(n===1?'No carrinho da Steam':n+' no carrinho da Steam')+(ja?` · ${ja} já estava${ja>1?'m':''}`:'')+(fora?` · ${fora} com melhor preço em outra loja ficou de fora`:''):'Já está no carrinho');},
  loja(a){open(storeUrl(a),'_blank','noopener');},
  lojaDe(a,loja){abrirNaLoja(a,loja);},   // a página do jogo na loja (o carrinho é só da Steam)
  irSecao(n){irSecao(n);},
  aba(t){setTab(t);},
  instalarExt(){instalarExt();},
  extVersao(){return document.documentElement.dataset.kurokamiExt||'';},
  sub(aba,s){if(FR[aba])FR[aba].sub=s;},
  dlcsPromo(){FR.bib.sub='completar:capas';setTab('bib');}   // o Completar em Capas abre na ordem "Em promoção": as DLCs com desconto de cada jogo
};
