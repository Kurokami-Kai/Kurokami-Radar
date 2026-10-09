/* ================= promoções (explorador; filtros no Hunter: /api/promocoes) ================= */
// Promoções e Lista de desejos (menu Ofertas) abrem sempre com estes filtros (sempre só Jogo, como os Destaques); +18 fica oculto sem o campo adulto
const P_PADRAO={desconto_min:50,analises_de:500,tipo:['jogo'],relacao:{tenho:'excluir'}};
let P=ls.get('promo',null)||JSON.parse(JSON.stringify(P_PADRAO)), PG=1, PP=ls.get('pp',100), PR=null, pSeq=0;
const salvarP=()=>{ls.set('promo',P);ls.set('pp',PP);};
function aplicarP(p){P=JSON.parse(JSON.stringify(p));PG=1;salvarP();}
try{localStorage.removeItem('kr:promo_antes');}catch(e){}  // do antigo atalho (até 08/10)
if(!ls.get('promo_v3',false)){aplicarP(P_PADRAO);ls.set('promo_v3',true);}  // 08/10: 500 análises e ✕ Tenho ao abrir
if(!ls.get('promo_v4',false)){if(P.relacao&&P.relacao.extra==='exigir'&&P.qualquer_um){delete P.relacao.extra;P.qualquer_um=false;salvarP();}ls.set('promo_v4',true);}  // o Ver tudo marcava Monitorado (até 08/10)
const REL=[['na_lista','Na lista de desejos'],['extra','Monitorado por você'],['no_carrinho','No carrinho'],['seguido','Seguido na Steam'],
  ['ignorado_steam','Ignorado na Steam'],['mudo','Silenciado'],['tenho','Tenho'],['base_tenho','Tenho o jogo base']];
const OUTROS_TXT={promo:'Só em promoção',bundle:'Em bundle',completo:'Modo completo',keyshop:'Keyshop bem mais barata'};
const COLS=[['nome','Jogo','asc'],['corte','%','desc'],['volta','Costuma voltar','asc'],['preco','Preço','asc'],['nota','Análises','desc'],
  ['lancamento','Lançamento','desc'],['fim','Termina','asc'],['inicio','Começou','desc']];
const COLNOME=Object.fromEntries(COLS.map(c=>[c[0],c[1]]));
function qPromo(){const q={pagina:PG,por_pagina:PP,fonte:'steam'};
  for(const [k,v] of Object.entries(P)){if(v==null||v===''||v===false)continue;if(Array.isArray(v)&&!v.length)continue;
    if(typeof v==='object'&&!Array.isArray(v)&&!Object.keys(v).length)continue;q[k]=v;}return q;}
async function renderLista(){
  const seq=++pSeq;let r;
  try{r=await api('/api/promocoes?q='+encodeURIComponent(JSON.stringify(qPromo())));}catch(e){return;}
  if(seq!==pSeq)return;PR=r;
  const maxPg=Math.max(1,Math.ceil(r.total/PP));if(PG>maxPg){PG=maxPg;return renderLista();}
  $('#cnt').textContent=fmtN(r.total);$('#listaTit').textContent=(P.relacao||{}).na_lista==='exigir'?'Lista de desejos':'Promoções';
  const st=r.steam||{};
  $('#listaNote').textContent=!st.ligada?'Steam inteira desligada em Configurações: mostrando só a sua lista.'
      :st.quando?`${fmtN(st.itens)} em promoção na Steam · atualizada ${relTempo(st.quando,false)}`
      :'A Steam inteira chega na próxima checagem (clique em Verificar agora para puxar já). Por enquanto, só a sua lista.';
  renderSide();renderChips();
  const box=$('#results');
  if(!r.itens.length)box.innerHTML='<div class="empty">Nenhum jogo com esses filtros.</div>';
  else box.innerHTML=S.pview==='grade'?`<div class="cgrid">${r.itens.map(capCard).join('')}</div>`:tabelaPromo(r.itens);
  $$('.views [data-view]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.view===S.pview));
  $('#pOrdG').hidden=S.pview!=='grade';
  const o0=(P.ordem||[['corte','desc'],['nome','asc']])[0];
  $('#pOrd').innerHTML=COLS.flatMap(([k,t])=>[['asc','↑'],['desc','↓']].map(([d,s])=>`<option value="${k}:${d}"${o0[0]===k&&o0[1]===d?' selected':''}>${t} ${s}</option>`)).join('');
  $('#pPP').value=String(PP);
  $('#pPager').innerHTML=paginas(PG,maxPg);
}
function paginas(pg,max){if(max<=1)return '';const ns=new Set([1,max,pg-2,pg-1,pg,pg+1,pg+2].filter(n=>n>=1&&n<=max));const l=[...ns].sort((a,b)=>a-b);
  let h=`<button data-pg="${pg-1}" ${pg<=1?'disabled':''}>‹</button>`,ant=0;
  l.forEach(n=>{if(n-ant>1)h+='<span>…</span>';h+=`<button data-pg="${n}" aria-current="${n===pg}">${n}</button>`;ant=n;});
  return h+`<button data-pg="${pg+1}" ${pg>=max?'disabled':''}>›</button>`;}
function relTempo(t,futuro){if(!t)return '';const ms=futuro?t*1000-Date.now():Date.now()-Date.parse(t);if(isNaN(ms))return '';const h=ms/36e5;
  if(futuro&&h<=0)return 'acabou';const d=Math.round(h/24);
  const txt=h<1?'menos de 1h':h<24?`${Math.round(h)}h`:`${d} dia${d>1?'s':''}`;return futuro?'em '+txt:'há '+txt;}
function recPill(o){const t=o.tipo_oferta;if(!t||t==='selo'||!(o.corte>0))return '';const r=o.piso_ref;
  return `<span class="pp pp-${t}" title="${esc(r?((t==='novo'?'recorde anterior: ':'menor de sempre: ')+pisoRefTxt(r)):'')}">${TIPO_NOME[t]}</span>`;}
/* calor da linha e das colunas da tabela de Promoções */
const rq=o=>o.selo?' class="rq3"':o.tipo_oferta==='novo'?' class="rq2"':o.tipo_oferta==='igual'?' class="rq1"':'';
const voltaQ=v=>v==null?'':v<2?' v3':v<=3.15?' v2':v<=5?' v1':' v0';   /* volta_ordem: 0-1 nunca/não em 2 anos; 2+promoções por ano */
function icones(o){return `${o.no_carrinho?'<span class="ico ico-carr" title="No carrinho">🛒</span>':''}${o.na_lista?'<span class="ico ico-lista" title="Na sua lista (desejos ou monitorado)">☰</span>':''}`;}
function tabelaPromo(it){const ord=P.ordem||[['corte','desc'],['nome','asc']];
  const th=(k,cls)=>{const i=ord.findIndex(x=>x[0]===k);const seta=i<0?'':(ord[i][1]==='asc'?'▲':'▼')+(ord.length>1?`<sup>${i+1}</sup>`:'');
    return `<th class="srt${cls?' '+cls:''}${i>=0?' on':''}" data-sort="${k}" title="Clique ordena; Shift+clique soma critérios">${COLNOME[k]} ${seta}</th>`;};
  return `<div class="ctab-wrap ptab-wrap"><table class="ctab ptab tnum"><thead><tr><th></th><th></th>${th('nome')}${th('corte','n')}${th('volta')}${th('preco','n')}${th('nota','n')}${th('lancamento','n')}${th('fim','n')}${th('inicio','n')}<th></th></tr></thead><tbody>
  ${it.map(o=>`<tr ${abre(o)}${rq(o)}><td class="icos">${icones(o)}</td><td class="pcap">${art(o.appid,o.nome,o.capa,{small:true})}</td>
    <td class="t"><span class="pnm">${esc(o.nome)}</span> ${o.selo?seloBadge(o):''}${recPill(o)}</td>
    <td class="n">${o.corte>0?`<span class="pct">-${o.corte}%</span>`:''}</td>
    <td class="volta${voltaQ(o.volta_ordem)}"${o.volta_dica?` title="${esc(o.volta_dica)}"`:''}>${o.volta_texto?esc(o.volta_texto):''}</td>
    <td class="n">${brl(o.preco)}</td><td class="n ${revClass(o.rpos,o.rcount)}" title="${o.rcount?fmtN(o.rcount)+' análises':''}">${o.rcount?o.rpos+'%':'—'}</td>
    <td class="n">${o.lancamento?new Date(o.lancamento*1000).toLocaleDateString('pt-BR'):(o.em_breve?'em breve':'')}</td><td class="n${o.fim&&o.fim*1000-Date.now()<3*864e5?' fim3':''}">${relTempo(o.fim,true)}</td><td class="n">${relTempo(o.inicio,false)}</td>
    <td>${cartBtn(o.appid,o.steam_inteira)}</td></tr>`).join('')}</tbody></table></div>`;}
function ordenarPor(k,somar){const padrao=(COLS.find(c=>c[0]===k)||[])[2]||'asc';let o=(P.ordem||[['corte','desc'],['nome','asc']]).map(x=>[...x]);
  const i=o.findIndex(x=>x[0]===k);
  if(somar){if(i>=0)o[i][1]=o[i][1]==='asc'?'desc':'asc';else o.push([k,padrao]);}
  else o=(i===0)?[[k,o[0][1]==='asc'?'desc':'asc']]:[[k,padrao]];
  P.ordem=o;PG=1;salvarP();renderLista();}
const reais=c=>c==null?'':String(c/100);
function renderSide(){const r=PR||{contagens:{mostrar_so:{},tipo:{}},conta:{tem_dados:false}};const ct=r.contagens,rel=P.relacao||{};
  const sem=!r.conta.tem_dados;
  const tri=(k,l)=>{const v=rel[k]||'';const off=sem&&(k==='seguido'||k==='ignorado_steam');
    return `<div class="tri${off?' off':''}"${off?' title="precisa dos dados da sua conta Steam"':''}><span>${l}</span><span class="tb" role="group" aria-label="${l}">
      <button data-rel="${k}" data-v="excluir" aria-pressed="${v==='excluir'}" title="esconder">✕</button><button data-rel="${k}" data-v="" aria-pressed="${!v}" title="tanto faz">—</button><button data-rel="${k}" data-v="exigir" aria-pressed="${v==='exigir'}" title="só esses">✓</button></span></div>`;};
  const caixa=(grupo,v,l,n,cor)=>`<label class="tick"><input type="checkbox" data-grupo="${grupo}" data-v="${v}" ${(P[grupo]||[]).includes(v)?'checked':''}>${cor?`<i class="dot" style="background:${cor}"></i>`:''}${l}${n!=null?`<span class="c">${fmtN(n)}</span>`:''}</label>`;
  const num=(k,ph,step)=>`<input type="number" class="pin" data-num="${k}" placeholder="${ph}" step="${step||1}" min="0" value="${k.startsWith('preco')?reais(P[k]):(P[k]??'')}">`;
  const sel=(k,l)=>`<label class="f">${l} <select data-sel="${k}"><option value="">—</option>${Array.from({length:20},(_,i)=>(i+1)*5).map(x=>`<option value="${x}"${P[k]===x?' selected':''}>${x}%</option>`).join('')}</select></label>`;
  const aberto=g=>(ls.get('aberto',{})[g])?' open':'';
  const marca=g=>(P[g]||[]).length?' <i class="pon"></i>':'';
  const ae=document.activeElement;let foco=null,pos=null;
  if(ae&&$('#pSide').contains(ae)){foco=ae.id?'#'+ae.id:ae.dataset.num?`[data-num="${ae.dataset.num}"]`:ae.dataset.data?`[data-data="${ae.dataset.data}"]`:null;try{pos=ae.selectionStart;}catch(e){}}
  $('#pSide').innerHTML=`<div class="blk"><h4>Buscar por nome</h4><div class="in"><label class="pbq"><svg viewBox="0 0 20 20" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="M13 13l4.5 4.5"/></svg><input type="search" id="pBusca" placeholder="Nome do jogo  ( Esc )" autocomplete="off" spellcheck="false" value="${esc(P.busca||'')}"></label></div></div>
    <div class="blk"><h4>Sua relação com o jogo</h4><div class="in">${REL.map(([k,l])=>tri(k,l)).join('')}
      <label class="tick"><input type="checkbox" id="pQq" ${P.qualquer_um?'checked':''}>Qualquer um (os ✓ valem com OU)</label>
      ${sem?`<div class="hint">Seguido e Ignorado vêm da sua conta Steam: ${temExt()&&parseFloat(document.documentElement.dataset.kurokamiExt)>=1.1?'abra qualquer página da loja da Steam (logado) e volte aqui':'precisa da extensão do Hunter 1.1 ou mais nova (instale, ou recarregue-a em chrome://extensions) e de uma visita à loja da Steam logado'}.</div>`:''}</div></div>
    <div class="blk"><h4>Conteúdo adulto (+18)</h4><div class="in"><span class="seg" role="group" aria-label="Conteúdo adulto">${[['','Ocultar'],['mostrar','Mostrar'],['so','Só +18']].map(([v,t])=>`<button data-adulto="${v}" aria-pressed="${(P.adulto||'')===v}">${t}</button>`).join('')}</span>
      <div class="hint">Pela classificação da Steam (conteúdo sexual). Jogos da sua lista nunca são ocultados.</div></div></div>
    <div class="blk"><h4>Mostrar só</h4><div class="in">${['selo','novo','igual','24m'].map(t=>caixa('mostrar_so',t,TIPO_NOME[t],ct.mostrar_so[t],TIPO_COR[t])).join('')}</div></div>
    <details class="blk"${aberto('tipo')} data-ab="tipo"><summary><h4>Tipo${marca('tipo')}</h4></summary><div class="in">${caixa('tipo','jogo','Jogo',ct.tipo.jogo)}${caixa('tipo','dlc','DLC',ct.tipo.dlc)}</div></details>
    <details class="blk"${aberto('outros')} data-ab="outros"><summary><h4>Outros${marca('outros')}</h4></summary><div class="in">${Object.entries(OUTROS_TXT).map(([k,l])=>caixa('outros',k,l)).join('')}</div></details>
    <div class="blk"><h4>Faixas</h4><div class="in pfx">
      <div class="f">Preço (R$) ${num('preco_de','de',1)} ${num('preco_ate','até',1)}</div>
      <div class="f">Análises ${num('analises_de','de',100)} ${num('analises_ate','até',100)}</div>
      ${sel('nota_min','Nota ≥')}${sel('desconto_min','Desconto ≥')}
      <div class="f">Lançamento <input type="date" class="pin" data-data="lanc_de" value="${esc(P.lanc_de||'')}"> <input type="date" class="pin" data-data="lanc_ate" value="${esc(P.lanc_ate||'')}"></div>
      <label class="tick"><input type="checkbox" id="pBreve" ${P.em_breve?'checked':''}>Só em breve</label>
      <div class="hint">Análises e nota filtram só a tela, nunca os avisos.</div></div></div>
    <div class="pbtns"><button class="btn-ghost" id="pLimpa" type="button">Limpar filtros</button><button class="btn-ghost" id="pPadrao" type="button">Restaurar padrão</button></div>`;
  if(foco){const n=$('#pSide '+foco);if(n){n.focus();try{if(pos!=null)n.setSelectionRange(pos,pos);}catch(e){}}}}
function chipsAtivos(){const c=[],R=P.relacao||{};
  if(P.busca)c.push(['busca',`"${P.busca}"`]);
  REL.forEach(([k,l])=>{if(R[k])c.push(['rel:'+k,(R[k]==='exigir'?'✓ ':'✕ ')+l]);});
  if(P.qualquer_um)c.push(['qualquer_um','Qualquer um']);
  (P.mostrar_so||[]).forEach(t=>c.push(['mostrar_so:'+t,TIPO_NOME[t]]));
  (P.tipo||[]).forEach(t=>c.push(['tipo:'+t,t==='dlc'?'DLC':'Jogo']));
  (P.outros||[]).forEach(t=>c.push(['outros:'+t,OUTROS_TXT[t]]));
  if(P.preco_de!=null)c.push(['preco_de','Preço ≥ '+brl(P.preco_de)]);if(P.preco_ate!=null)c.push(['preco_ate','Preço ≤ '+brl(P.preco_ate)]);
  if(P.analises_de!=null)c.push(['analises_de','Análises ≥ '+fmtN(P.analises_de)]);if(P.analises_ate!=null)c.push(['analises_ate','Análises ≤ '+fmtN(P.analises_ate)]);
  if(P.nota_min!=null)c.push(['nota_min','Nota ≥ '+P.nota_min+'%']);if(P.desconto_min!=null)c.push(['desconto_min','Desconto ≥ '+P.desconto_min+'%']);
  if(P.lanc_de)c.push(['lanc_de','Lançado desde '+P.lanc_de.split('-').reverse().join('/')]);if(P.lanc_ate)c.push(['lanc_ate','Lançado até '+P.lanc_ate.split('-').reverse().join('/')]);
  if(P.em_breve)c.push(['em_breve','Só em breve']);
  if(P.adulto)c.push(['adulto',P.adulto==='so'?'Só +18':'+18 incluídos']);
  return c;}
function renderChips(){const c=chipsAtivos();
  $('#pChips').innerHTML=c.map(([k,t])=>`<span class="pchip">${esc(t)}<button data-tira="${esc(k)}" aria-label="Tirar o filtro ${esc(t)}">×</button></span>`).join('');}
function tirarFiltro(k){const [g,v]=k.split(':');
  if(g==='rel'){const R={...(P.relacao||{})};delete R[v];P.relacao=R;}
  else if(v!==undefined)P[g]=(P[g]||[]).filter(x=>x!==v);
  else delete P[g];
  PG=1;salvarP();renderLista();}
let pT=null;
function mudouP(atraso){PG=1;salvarP();clearTimeout(pT);pT=setTimeout(renderLista,atraso||0);}
$('#pSide').addEventListener('click',e=>{const b=e.target.closest('[data-rel]');
  if(b){if(b.closest('.tri.off'))return;const R={...(P.relacao||{})};if(b.dataset.v)R[b.dataset.rel]=b.dataset.v;else delete R[b.dataset.rel];P.relacao=R;mudouP();return;}
  const ad=e.target.closest('[data-adulto]');if(ad){if(ad.dataset.adulto)P.adulto=ad.dataset.adulto;else delete P.adulto;mudouP();return;}
  if(e.target.id==='pLimpa'){P={};mudouP();return;}
  if(e.target.id==='pPadrao'){P=JSON.parse(JSON.stringify(P_PADRAO));mudouP();return;}});
$('#pSide').addEventListener('change',e=>{const t=e.target;
  if(t.dataset.grupo){const g=t.dataset.grupo,v=t.dataset.v;const l=new Set(P[g]||[]);t.checked?l.add(v):l.delete(v);P[g]=[...l];mudouP();return;}
  if(t.id==='pQq'){P.qualquer_um=t.checked;mudouP();return;}
  if(t.id==='pBreve'){P.em_breve=t.checked;mudouP();return;}
  if(t.dataset.sel){const v=t.value;if(v==='')delete P[t.dataset.sel];else P[t.dataset.sel]=+v;mudouP();return;}
  if(t.dataset.data){if(t.value)P[t.dataset.data]=t.value;else delete P[t.dataset.data];mudouP();return;}});
$('#pSide').addEventListener('input',e=>{const t=e.target;
  if(t.id==='pBusca'){P.busca=t.value.trim();if(!P.busca)delete P.busca;mudouP(250);return;}
  if(t.dataset.num){const k=t.dataset.num,v=t.value.trim().replace(',','.');
    if(v===''||isNaN(+v))delete P[k];else P[k]=k.startsWith('preco')?Math.round(+v*100):Math.round(+v);mudouP(250);}});
$('#pSide').addEventListener('toggle',e=>{const d=e.target.closest('details[data-ab]');if(!d)return;const a=ls.get('aberto',{});a[d.dataset.ab]=d.open;ls.set('aberto',a);},true);
$('#pChips').addEventListener('click',e=>{const b=e.target.closest('[data-tira]');if(b)tirarFiltro(b.dataset.tira);});
$('#results').addEventListener('click',e=>{const h=e.target.closest('th[data-sort]');if(!h)return;e.preventDefault();e.stopPropagation();ordenarPor(h.dataset.sort,e.shiftKey);},true);
$('#pPager').addEventListener('click',e=>{const b=e.target.closest('[data-pg]');if(!b||b.disabled)return;PG=+b.dataset.pg;renderLista();$('#tab-lista').scrollIntoView({block:'start'});});
$('#pPP').addEventListener('change',e=>{PP=+e.target.value;PG=1;salvarP();renderLista();});
$('#pOrd').addEventListener('change',e=>{const [k,d]=e.target.value.split(':');P.ordem=[[k,d]];PG=1;salvarP();renderLista();});
$$('.views [data-view]').forEach(b=>b.addEventListener('click',()=>{S.pview=b.dataset.view;save();renderLista();}));
$('#pfBtn').addEventListener('click',()=>{const s=$('#pSide');s.classList.toggle('open');$('#pfBtn').setAttribute('aria-expanded',s.classList.contains('open'));});
