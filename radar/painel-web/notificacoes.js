/* ================= notificações ================= */
let NOTIF=[];
// etiqueta pelo começo do motivo (analise.motivo_tipo); o 4º item diz se o texto fica inteiro
const NF_TIPOS=[[/^Selo Kurokami:\s*/i,'Selo Kurokami','#ff4757'],[/^menor preço já registrado/i,'Novo recorde','#ff4757',1],
  [/^mesmo preço do menor/i,'Igual ao recorde','#ff8a94',1],[/^menor preço em 2 anos/i,'Menor em 2 anos','#979797',1],
  [/^keyshop\s*/i,'Keyshop','#979797'],[/^versão completa/i,'Versão completa','#d2d2d2',1]];
const nfKey=n=>/keyshop/i.test(n.loja||'');
function nfTipo(n){const m=n.motivo||'',r=NF_TIPOS.find(x=>x[0].test(m));let t,c='#979797',txt=m;
  if(r){t=r[1];c=r[2];if(!r[3])txt=m.replace(r[0],'');}
  else{const p=m.match(/^([^:]{2,20}):\s*/);if(p){t=p[1];txt=m.slice(p[0].length);}else t=nfKey(n)?'Keyshop':'Promoção';}
  return {t,c,txt:txt?txt[0].toUpperCase()+txt.slice(1):''};}
function nfDia(iso){const d=new Date(iso),z=x=>new Date(x.getFullYear(),x.getMonth(),x.getDate()).getTime(),dd=Math.round((z(new Date())-z(d))/864e5);
  return dd===0?'Hoje':dd===1?'Ontem':d.toLocaleDateString('pt-BR',{weekday:'long',day:'2-digit',month:'2-digit'}).replace(/^./,c=>c.toUpperCase());}
const nfHora=iso=>new Date(iso).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
function nfAgora(n){const o=IDX.get(n.appid);if(!o)return '';const k=nfKey(n),p=k?o.keyshop:o.preco;
  if(p==null)return '<span class="nf-ag up">sem preço agora</span>';
  if(!k&&!(o.corte>0)&&p>n.preco)return `<span class="nf-ag up">a promoção acabou · ${brl(p)}</span>`;
  return p<n.preco?`<span class="nf-ag ok">agora ${brl(p)}, mais barato</span>`:p===n.preco?'<span class="nf-ag ok">ainda nesse preço</span>':`<span class="nf-ag">agora ${brl(p)}</span>`;}
async function renderNotif(){const d=await api('/api/notificacoes');NOTIF=d.itens||[];desenharNotif();}
function desenharNotif(){
  if(!NOTIF.length){$('#notifTopo').innerHTML='';$('#notifLista').innerHTML='<div class="empty">Nenhuma notificação ainda. A primeira checagem só registra o que já está em promoção; daí em diante, as novidades aparecem aqui.</div>';return;}
  // o mesmo jogo pela mesma via (loja oficial ou keyshop) aparece uma vez, no aviso mais recente, com os anteriores contados
  const por=new Map(),lista=[];
  for(const n of NOTIF){const k=n.appid+(nfKey(n)?'k':'o'),a=por.get(k);if(a){a.antes.push(n);continue;}const x={...n,antes:[]};por.set(k,x);lista.push(x);}
  const nk=lista.filter(nfKey).length,f=S.nf||'todas',vis=lista.filter(n=>f==='todas'||(f==='keyshop')===nfKey(n));
  const desde=new Date(NOTIF[NOTIF.length-1].quando).toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit'});
  $('#notifTopo').innerHTML=`<div class="nf-bar"><div class="nf-seg">${[['todas','Todas',lista.length],['oficial','Lojas oficiais',lista.length-nk],['keyshop','Keyshops',nk]].map(([k,t,c])=>`<button type="button" data-nf="${k}" aria-pressed="${f===k}">${t}<span>${c}</span></button>`).join('')}</div>
    <span class="nf-info">${fmtN(NOTIF.length)} aviso${NOTIF.length>1?'s':''} desde ${desde}${NOTIF.length>=200?' (os 200 mais recentes)':''} · o mesmo jogo aparece uma vez</span></div>`;
  const dias=[];for(const n of vis){const dl=nfDia(n.quando);if(!dias.length||dias[dias.length-1][0]!==dl)dias.push([dl,[]]);dias[dias.length-1][1].push(n);}
  $('#notifLista').innerHTML=vis.length?dias.map(([dl,l])=>`<h3 class="nf-dia">${esc(dl)}<span>${l.length} jogo${l.length>1?'s':''}</span></h3><div class="nf-grupo">${l.map(n=>{const t=nfTipo(n),a=n.antes;
    return `<div class="nf-row" data-open="${n.appid}">${art(n.appid,n.nome||n.appid,n.capa)}
    <div style="min-width:0"><div class="nf-nome">${esc(n.nome||n.appid)}</div><div class="nf-mot"><span class="nf-tag" style="--c:${t.c}">${esc(t.t)}</span><span>${esc(t.txt)}</span></div>
    <div class="nf-meta">${esc(n.loja||'')} · ${nfHora(n.quando)}${a.length?` · avisado ${a.length+1} vezes; antes ${a.slice(0,2).map(x=>brl(x.preco)+' em '+fmtISO(x.quando).replace(',',' às')).join(', ')}`:''}</div></div>
    <div class="nf-preco"><span class="nf-p tnum">${brl(n.preco)}</span>${nfAgora(n)}</div>${cartBtn(n.appid)}</div>`;}).join('')}</div>`).join('')
    :`<div class="empty">Nenhuma notificação de ${f==='keyshop'?'keyshop':'loja oficial'}.</div>`;
}
$('#tab-notif').addEventListener('click',e=>{const b=e.target.closest('[data-nf]');if(b){S.nf=b.dataset.nf;save();desenharNotif();return;}
  if(e.target.closest('[data-nfcfg]')){e.preventDefault();ls.set('cfgSec','avisos');setTab('cfg');window.scrollTo(0,0);}});
