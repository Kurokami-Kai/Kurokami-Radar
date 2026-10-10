/* ================= modal do jogo ================= */
function porqueVolta(m){const o=IDX.get(m.jogo.appid)||{};
  const selo=m.selo?`<div style="margin-bottom:6px">${seloBadge(m)} <b>${esc((m.selo_motivo||'').replace(/^./,c=>c.toUpperCase()))}</b><br>
    O menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade. Nos dados de 2022–2025, em cerca de 7 de 10 casos assim o jogo não ficou mais barato nos 12 meses seguintes.</div>`:'';
  const volta=m.volta_texto?`<b>Costuma voltar: ${esc(m.volta_texto)}</b>${m.volta_dica?`<br>${esc(m.volta_dica)}`:''}`:'';
  const ref=m.piso_ref&&m.corte>0?`${volta?'<br>':''}Menor preço antes desta promoção: <b>${esc(pisoRefTxt(m.piso_ref))}</b>`:'';
  const regua=m.regua_steam?`<div class="regua">${esc(m.regua_steam.texto)}</div>`:'';
  return selo||volta||ref?`<div class="porque">${selo}${volta}${ref}</div>${regua}`:regua;}
let MJ=null, MRANGE=365, MVISTA='steam';   // MVISTA: o gráfico da ficha, 'steam' (como o SteamDB) ou 'todas' (tecla T)
let MSEQ=0;
async function abrirJogo(appid,op){
  const meu=++MSEQ;MOP=op||{};
  $$('#modal .mnav').forEach(b=>b.hidden=!MOP.passo);$('#mpos').hidden=!MOP.pos;$('#mpos').textContent=MOP.pos||'';
  if(op){window.focus();setTimeout(()=>{const c=$('#modal .mclose');if(c)c.focus({preventScroll:true});},0);}
  $('#modal').hidden=false;$('#modal').scrollTop=0;document.body.style.overflow='hidden';$('#mbody').innerHTML='<div class="empty">carregando… (fora da lista, o histórico vem da IsThereAnyDeal na hora)</div>';
  MX=undefined;MTROCA=false;   // descrição, HLTB, notas e conquistas chegam depois, para a ficha abrir na hora
  const extra=fetch('/api/jogo_extra?appid='+appid).then(r=>r.ok?r.json():{falhou:true}).catch(()=>({falhou:true}));
  let j;try{j=await api('/api/jogo?appid='+appid);}catch(e){if(meu===MSEQ)$('#mbody').innerHTML=`<div class="empty">Erro: ${esc(e.message)}</div>`;return;}
  if(meu!==MSEQ)return;MJ=j;
  renderModal();
  const x=await extra;if(meu===MSEQ&&!$('#modal').hidden){MX=x;renderModal();}
}
function fecharModal(){$('#modal').hidden=true;document.body.style.overflow='';if(FR[S.tab])focaFrame();MOP={};}
$('#modal').addEventListener('click',e=>{const p=e.target.closest('[data-mpasso]');if(p){if(MOP.passo)MOP.passo(+p.dataset.mpasso);return;}
  if(e.target.id==='modal'||e.target.closest('.mclose'))fecharModal();});
addEventListener('keydown',e=>{if($('#modal').hidden)return;if(e.key==='Escape')fecharModal();
  else if(e.shiftKey&&/^Digit[1-5]$/.test(e.code)&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&$('#fxPainel')&&!/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)){const a=fxListaAbas()[+e.code.slice(5)-1];if(a){e.preventDefault();const foco=e.target.closest&&e.target.closest('.fx-aba');fxAba(a[0]);if(foco)$('#mbody .fx-aba[aria-selected="true"]').focus({preventScroll:true});}}
  else if((e.key==='t'||e.key==='T')&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&$('#chart')&&!/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)){e.preventDefault();fxVista(MVISTA==='steam'?'todas':'steam');}
  else if(MOP.passo&&(e.key==='ArrowLeft'||e.key==='ArrowRight')&&!/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)){e.preventDefault();MOP.passo(e.key==='ArrowRight'?1:-1);}});
/* a caixa do veredito das páginas novas (amostra 8): o veredito numa linha, 2 frases e o "por quê" fechado */
function fxVered(v){return `<div class="fx-cx fx-v8" style="--c:${v.cor}"><div class="l1">${v.etq?`<span class="fx-etq" style="background:${v.etq[1]};color:${v.etq[2]}">${esc(v.etq[0])}</span>`:''}<span><b style="color:${v.cor}">${esc(v.rot)}</b>${v.sub?' · '+esc(v.sub):''}</span></div>
  ${v.fatos.length?`<div class="fts">${v.fatos.map(([a,b,n])=>`<div><span class="k">${esc(a)}</span><b>${esc(b)}</b>${n?`<small>${esc(n)}</small>`:''}</div>`).join('')}</div>`:''}
  ${v.fora?'<div class="fx-vazio" style="margin-top:6px">Fora de venda nas suas lojas.</div>':''}${v.selo?`<div class="selo-m">Selo Kurokami: ${esc(v.selo)}.</div>`:''}
  ${v.porque.length?`<details><summary>por quê</summary>${v.porque.map(x=>`<p>${esc(x)}</p>`).join('')}</details>`:''}</div>`;}
function dlcMotivo(e){
  if(!e)return '';
  const t=e.motivo==='falhou'?`A consulta de DLCs falhou em ${fmtISO(e.quando)}; o Hunter tenta de novo na próxima verificação.`
    :e.motivo==='sem_dlcs'?`A Steam não informou DLCs para este jogo (consultado em ${fmtISO(e.quando)}).`
    :e.fila?`Lista de DLCs ainda não consultada — verificação em andamento, ${fmtN(e.fila.atual)}/${fmtN(e.fila.total)} jogos.`
    :'Lista de DLCs ainda não consultada; entra na próxima verificação.';
  return `<h4>DLCs</h4><div class="hint" style="color:var(--dim);font-size:12px">${t}</div>`;
}
/* ficha nova (spec 09, amostra B+): a mesma em Ofertas, Promoções e Biblioteca; só mudam os blocos (tenho ou não).
   MX = o que vem de /api/jogo_extra (descrição, captura, HLTB, notas, conquistas): undefined enquanto busca. */
const CDNA='https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/';
const horas=m=>m==null?'—':(m/60).toLocaleString('pt-BR',{maximumFractionDigits:m<600?1:0})+' h';
const TITULO_TIPO={novo:'Nunca esteve tão barato',igual:'Igual ao menor preço de sempre','24m':'O menor preço em 2 anos'};
let MX, MTROCA=false;const MFUNDO={}, SEM_LOGO=new Set();
const capaV=m=>m.capa_v||CDNA+m.appid+'/library_600x900_2x.jpg';
function imgV(m,cls){return `<img${cls?` class="${cls}"`:''} src="${esc(capaV(m))}" alt="" loading="lazy" data-ph="${esc(m.nome)}" data-id="${m.appid}"${m.capa?` data-alt="${esc(m.capa)}"`:''}>`;}
function corDaCapa(url){return new Promise(r=>{const i=new Image();i.crossOrigin='anonymous';
  i.onload=()=>{try{const c=document.createElement('canvas');c.width=24;c.height=36;const x=c.getContext('2d');x.drawImage(i,0,0,24,36);
    const d=x.getImageData(0,0,24,36).data;let R=0,G=0,B=0,W=0;   // média pesada pela saturação: a cor da capa, não o cinza
    for(let k=0;k<d.length;k+=4){const w=Math.max(d[k],d[k+1],d[k+2])-Math.min(d[k],d[k+1],d[k+2])+8;R+=d[k]*w;G+=d[k+1]*w;B+=d[k+2]*w;W+=w;}
    r(`rgb(${R/W*.55|0},${G/W*.55|0},${B/W*.55|0})`);}catch(e){r('#050505');}};
  i.onerror=()=>r('#050505');i.src=url;});}
function fxTile(l,v,sub,cls){return `<div class="fx-tile${cls?' '+cls:''}"><small>${l}</small><b>${v}</b>${sub?`<span>${sub}</span>`:''}</div>`;}
function fxAnel(p){const r=14,c=2*Math.PI*r;return `<svg viewBox="0 0 34 34" width="34" height="34" aria-hidden="true"><circle cx="17" cy="17" r="${r}" fill="none" stroke="#ffffff1a" stroke-width="4"/><circle cx="17" cy="17" r="${r}" fill="none" stroke="#ff4757" stroke-width="4" stroke-dasharray="${(c*p).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 17 17)"/></svg>`;}
const fxBusca=(t,nada)=>MX===undefined?t:nada;
function fxTiles(){
  const j=MJ.jogo,o=MJ.item||IDX.get(j.appid)||{},a=MX&&MX.aug,h=a&&a.hltb;
  const anal=j.rcount?fxTile('Análises',j.rpos+'%',`${esc(j.rotulo||'')} · ${fmtN(j.rcount)}`):fxTile('Análises','—','sem análises');
  const semH=fxTile('Para zerar',fxBusca('…','—'),fxBusca('buscando no HowLongToBeat','sem dados do HowLongToBeat'));
  if(MJ.tenho){
    const jg=MJ.jogado,min=jg&&jg.minutos,c=MX&&MX.conq;
    const conq=c&&c.total?`<div class="fx-tile"><small>Conquistas</small><div class="fx-anel">${fxAnel(c.feitas/c.total)}<b>${c.feitas}/${c.total}</b></div><span>${c.feitas===c.total?'platinado':Math.round(c.feitas/c.total*100)+'% · faltam '+(c.total-c.feitas)}</span></div>`
      :fxTile('Conquistas',c?'—':fxBusca('…','—'),c?'sem conquistas':fxBusca('buscando…',MX&&MX.falhou?'não deu para buscar':MX&&!('conq' in MX)?'precisa da chave da Steam':'perfil com jogos privados?'));
    const st=j.preco_steam,cs=j.desconto_steam>0;
    return `<div class="fx-tiles">${fxTile('Tempo jogado',jg?horas(min||0):'—',jg?(jg.ultima?'última vez '+fmtUnix(jg.ultima):'nunca jogado'):'vem na próxima verificação')}${conq}
      ${h&&h.story?fxTile('Para zerar',horas(h.story),min?`você: ${Math.round(min/h.story*100)}%${h.complete?' · '+horas(h.complete)+' tudo':''}`:(h.complete?horas(h.complete)+' para completar':'')):semH}
      ${anal}${fxTile('Na Steam hoje',st!=null?`${cs?`<span class="pc">-${j.desconto_steam}%</span>`:''}${brl(st)}`:'—',st!=null?'para dar de presente':'sem preço',cs?'verde':'')}</div>`;
  }
  const cheio=(MJ.lojas.find(l=>l.loja===o.loja)||{}).cheio;
  const melhor=o.preco!=null?fxTile('Melhor preço',`${MJ.corte>0?`<span class="pc">-${MJ.corte}%</span>`:''}${brl(o.preco)}`,`na ${esc(o.loja||'')}${cheio&&cheio>o.preco?' · de '+brl(cheio):''}`,MJ.corte>0?'verde':'')
    :fxTile('Preço',brl(j.preco_steam),'na Steam');
  const crit=a&&(a.meta!=null||a.oc!=null)?fxTile('Crítica',[a.meta,a.oc].filter(x=>x!=null).join(' · '),[a.meta!=null?'Metacritic':'',a.oc!=null?'OpenCritic':''].filter(Boolean).join(' · '))
    :fxTile('Crítica',fxBusca('…','—'),fxBusca('buscando…','sem notas'));
  return `<div class="fx-tiles">${melhor}${MJ.fim?fxTile('Termina',relTempo(MJ.fim,true),fmtUnix(MJ.fim)):fxTile('Termina','—',MJ.corte>0?'sem data informada':'sem promoção')}
    ${anal}${h&&h.story?fxTile('Para zerar',horas(h.story),h.complete?horas(h.complete)+' para completar':''):semH}${crit}</div>`;
}
function fxAcoes(){
  const j=MJ.jogo,o=MJ.item||IDX.get(j.appid)||{},noC=CARR.find(c=>c.appid===j.appid);
  // a loja do preço mais barato de agora nas suas lojas (no empate, a Steam): o botão diz onde vai comprar
  const ml=(MJ.lojas||[]).filter(l=>l.marcada&&l.atual!=null).sort((a,b)=>a.atual-b.atual||(a.loja!=='Steam')-(b.loja!=='Steam'))[0];
  const fora=ml&&ml.loja!=='Steam';   // o melhor preço é de outra loja: o botão principal abre a página dela (o carrinho é só da Steam)
  const vendeSteam=(MJ.lojas||[]).some(l=>l.loja==='Steam'&&l.atual!=null);
  const bt=(at,t,cls)=>`<button class="${cls||'btn-ghost'}" ${at}>${t}</button>`;
  const loja=`<a class="btn-ghost" href="${storeUrl(j.appid)}" target="_blank" rel="noopener">Página na Steam</a>`;
  if(MJ.tenho)return `<div class="fx-acoes"><a class="btn-go" href="steam://run/${j.appid}">▶ Jogar na Steam</a>${loja}${MJ.tenho_manual?bt('data-tenho="1"','Desfazer "já tenho"'):''}</div>`;
  const carro=fora&&!noC?(/^https:\/\//.test(ml.url||'')?`<a class="btn-go green" href="${esc(ml.url)}" target="_blank" rel="noopener">Abrir na ${esc(ml.loja)} ↗</a>`:bt(`data-mloja="${esc(ml.loja)}"`,'Abrir na '+esc(ml.loja)+' ↗','btn-go green'))
    +(vendeSteam?bt(`data-mcart="${j.appid}"`,'Pôr no carrinho da Steam','btn-ghost'):''):bt(`data-mcart="${j.appid}"`,noC?'✓ No carrinho da Steam':'Pôr no carrinho da Steam','btn-go green');
  return `<div class="fx-acoes">${carro}${loja}${bt('data-tenho="1"','Já tenho')}
    ${o.extra?bt(`data-desmonitorar="${j.appid}"`,'Parar de monitorar'):''}${MJ.steam_inteira?bt(`data-monitorar="${j.appid}" title="Entra na sua lista do Hunter: alertas, todas as lojas, DLCs e keyshop"`,'Monitorar'):''}
    ${bt(`data-mudo="${MJ.mudo?0:1}"`,MJ.mudo?'Voltar a avisar':'Não avisar deste jogo')}
    ${MJ.dlcs.length?`<span class="seg" role="group" aria-label="Alertar por"><button data-modo="base" aria-pressed="${MJ.modo!=='completo'}">Alertar pelo base</button><button data-modo="completo" aria-pressed="${MJ.modo==='completo'}">Pelo completo</button></span>`:''}</div>`;
}
function fxFileira(){
  const F=MJ.franquia;if(!F||F.total<2)return '';const a=MJ.jogo.appid;
  return `<div class="fx-car"><div class="topo2"><h3>Sequências e franquia</h3><span class="q">${esc(F.nome)} · tenho ${F.tenho} de ${F.total}</span><span class="fx-prog"><i style="width:${F.tenho/F.total*100}%"></i></span></div>
    <button class="fx-seta e" data-car="-1" aria-label="Anteriores" hidden>‹</button><button class="fx-seta d" data-car="1" aria-label="Próximos" hidden>›</button>
    <div class="fx-trilho">${F.membros.map(m=>`<a href="#" class="fx-capa${m.tenho?'':' falta'}${m.appid===a?' atual':''}" data-ficha="${m.appid}" title="${esc(m.nome+(m.tenho?' (tenho)':m.lista?' (na lista de desejos)':' (não tenho)'))}">${imgV(m)}
      ${m.tenho?'<span class="sel ok">✓</span>':m.lista?'<span class="sel cor">♥</span>':''}<div class="nm">${esc(m.nome)}</div>
      <div class="ano">${m.lancamento?new Date(m.lancamento*1000).getFullYear():m.em_breve?'em breve':''}${!m.tenho&&m.preco!=null?` · <span class="pr">${brl(m.preco)}</span>`:''}</div></a>`).join('')}</div></div>`;
}
/* painel 1: vale a pena (ou seu progresso, se já tem) */
function fxVale(){
  const o=MJ.item||IDX.get(MJ.jogo.appid)||{};let s='';
  if(MJ.tenho){
    const c=MX&&MX.conq,tem=MJ.dlcs.filter(d=>d.tenho),faltam=MJ.dlcs.filter(d=>!d.tenho&&d.conta);
    const conq=c&&c.total?`<div style="font-size:13px;color:var(--muted)">Conquistas · ${c.feitas} de ${c.total}</div><div class="fx-barra"><i style="width:${c.feitas/c.total*100}%"></i></div>
      <div class="fx-vazio" style="margin-bottom:12px">${c.feitas===c.total?'Platinado: todas as conquistas':'Faltam '+(c.total-c.feitas)+' para platinar'}</div>`:'';
    const dl=MJ.dlcs.length?`<div style="font-size:13px;color:var(--muted);margin-bottom:2px">DLCs · tenho ${tem.length} de ${MJ.dlcs.length}${faltam.length?` · faltam ${faltam.length} que contam`:''}</div>
      ${faltam.slice(0,6).map(d=>`<div class="fx-l"><span>${esc(d.nome||d.appid)}</span><span>${brl(d.preco)}</span></div>`).join('')}`:'';
    return conq||dl?`<div class="fx-cx">${conq}${dl}</div>`:'<div class="fx-vazio">Sem conquistas nem DLCs para acompanhar.</div>';
  }else{
    const pv=porqueVolta(MJ),t=!MJ.selo&&MJ.corte>0&&TITULO_TIPO[MJ.tipo_oferta];
    if(MOP.vered)s+=fxVered(MOP.vered);
    else if(pv||t)s+=`<div class="fx-cx fx-vered">${t?`<div class="t">${recPill({tipo_oferta:MJ.tipo_oferta,corte:MJ.corte,piso_ref:MJ.piso_ref})}${t}</div>`:''}${pv}</div>`;
    s+=fxPisos(o);
  }
  return s||`<div class="fx-vazio">${MJ.corte>0?'Ainda sem histórico para dizer se vale a pena.':'Sem promoção agora: o Hunter avisa quando o preço cair.'}</div>`;
}
/* "menor preço antes desta promoção" pelo melhor preço de cada dia nas lojas que alertam (o mesmo do gráfico):
   o preço de agora fica fora, senão toda janela repetia o preço de hoje; janelas com o mesmo valor viram uma caixa só */
function fxPisos(o){
  const {env,marc}=fxEnvMarc();if(!env.length)return '';
  const agora=Date.now(),p=o.preco!=null?o.preco:(MJ.lojas.filter(l=>l.marcada&&l.atual!=null).map(l=>l.atual).sort((a,b)=>a-b)[0]??null),promo=MJ.corte>0&&p!=null;let ini=agora;
  if(promo)for(let i=env.length-1;i>=0&&env[i][1]<=p+tolP(p);i--)ini=env[i][0];   // como analise._igual: o preço de agora ou menor
  const menor=d=>{const t0=agora-d*DIA_MS;let m=null;
    env.forEach((x,i)=>{const f=i+1<env.length?env[i+1][0]:agora;if(f>t0&&x[0]<ini&&(!m||x[1]<=m[0]))m=[x[1],Math.min(f,ini)];});return m;};
  const J=[[90,'3 meses'],[180,'6 meses'],[365,'1 ano'],[730,'2 anos'],[1e6,'De sempre']].map(([d,t])=>[t,menor(d)]).filter(x=>x[1]);
  const titulo=`${promo?'Menor preço antes desta promoção':'Menor preço'} <span class="q">${marc?'nas lojas que alertam':'em todas as lojas'}</span>`;
  const geral=o.piso_geral!=null&&o.piso!=null&&o.piso_geral<o.piso?`<div class="fx-vazio" style="margin-top:6px">Em lojas que não alertam já teve ${brl(o.piso_geral)}.</div>`:'';
  if(!J.length)return `<div><h3>${titulo}</h3><div class="fx-vazio">Antes desta promoção não há preço registrado: ela começou junto com o histórico.</div>${geral}</div>`;
  const G=[];J.forEach(([t,m])=>{const u=G[G.length-1];if(u&&u.v===m[0])u.t.push(t);else G.push({v:m[0],q:m[1],t:[t]});});
  const rot=t=>t.length===1?t[0]:t[t.length-1]==='De sempre'?(t.length===J.length?'De sempre':t[0]+' ou mais'):t[0]+' a '+t[t.length-1];
  const cmp=v=>!promo?'':p<v-tolP(v)?`<span class="on">agora ${brl(v-p)} a menos</span>`:p<=v+tolP(v)?'<span>agora igual</span>':`<span>agora ${brl(p-v)} a mais</span>`;
  return `<div><h3>${titulo}</h3><div class="pisos tnum" style="grid-template-columns:repeat(${G.length},minmax(0,1fr));max-width:${G.length*230}px">${G.map(g=>`<div class="${promo&&p<g.v-tolP(g.v)?'on':''}">${rot(g.t)}<b>${brl(g.v)}</b><small>em ${fmtMes(g.q-1)}</small>${cmp(g.v)}</div>`).join('')}</div>${geral}</div>`;
}
/* painel 2: histórico de preços */
function fxHist(){let s='';
  if(Object.keys(MJ.historico).length)s+=`<div><h3>Histórico de preços <span class="seg">${[[90,'3 meses'],[365,'1 ano'],[1095,'3 anos'],[99999,'Tudo']].map(([d,t])=>`<button data-range="${d}" aria-pressed="${MRANGE===d}">${t}</button>`).join('')}</span></h3>
    ${MJ.steam_inteira?`<div class="fx-vazio" style="color:${MJ.aviso_hist?'#ff8a94':''};margin-bottom:6px">${MJ.aviso_hist?'Sem histórico: '+esc(MJ.aviso_hist)+'.':'Fora da sua lista: histórico das suas lojas marcadas (IsThereAnyDeal); das outras lojas só o menor preço. Para alertas e todas as lojas, use Monitorar.'}</div>`:''}
    <div class="chart" id="chart"></div><div class="legend" id="legend"></div></div><div class="fx-faixa" id="faixa"></div>`;
  return s||'<div class="fx-vazio">Sem histórico de preços ainda.</div>';
}
function fxCaminhos(){let s='';
  if(MJ.caminhos.length)s+=`<div><h4>Formas de comprar</h4><div class="ctab-wrap"><table class="ctab tnum"><thead><tr><th>Opção</th><th class="n">Seu preço</th><th class="n">Cobre</th><th class="n">p/ completar</th></tr></thead><tbody>
    ${MJ.caminhos.map(c=>`<tr title="${esc((c.itens||[]).map(i=>i.nome+(i.tenho?' (tenho)':'')).join('\n'))}"><td class="t">${esc(c.nome)}${c.tipo==='parcial'?'<span class="tag">parcial</span>':''}${c.extras_lista&&c.extras_lista.length?`<span class="tag">+${c.extras_lista.length} da lista</span>`:''}</td>
      <td class="n">${brl(c.preco)}</td><td class="n">${c.cobertura}%${c.estimada?'~':''}</td><td class="n">${brl(c.custo_completo)}</td></tr>`).join('')}</tbody></table></div>
    ${MJ.combo?`<div class="combo">Jeito mais barato de ter tudo: <b>${brl(MJ.combo.custo_completo)}</b><ul>${MJ.combo.partes.map(p=>`<li>${esc(p[0])} — ${brl(p[1])}</li>`).join('')}${MJ.combo.avulsos.map(a=>`<li>${esc(a.nome)} (avulso) — ${brl(a.preco)}</li>`).join('')}</ul></div>`:''}</div>`;
  return s;
}
function fxDlcs(){let s='';
  const opts=k=>Object.entries(MJ.classes).map(([v,t])=>`<option value="${v}"${v===k?' selected':''}>${esc(t)}</option>`).join('');
  s+=MJ.dlcs.length?`<div><h4>DLCs (${MJ.dlcs.length})</h4><div class="ctab-wrap"><table class="ctab tnum"><thead><tr><th>DLC</th><th>Classe</th><th class="n">Preço</th></tr></thead><tbody>
    ${MJ.dlcs.map(d=>`<tr class="${d.conta?'':'off'}"><td class="t">${esc(d.nome||d.appid)}${d.tenho?'<span class="tag">tenho</span>':''}${d.origem==='usuario'?'<span class="tag">você marcou</span>':''}</td>
      <td><select class="mini" data-dlc="${d.appid}">${opts(d.classe)}</select></td><td class="n">${brl(d.preco)}</td></tr>`).join('')}</tbody></table></div>
    <div class="fx-vazio" style="margin-top:6px">Itens apagados não entram no custo completo (veja as opções de DLC em Configurações).</div></div>`:`<div>${dlcMotivo(MJ.dlcs_estado)}</div>`;
  return s;
}
function fxTroca(F){return `<div class="fx-troca"><input id="frNome" list="frNomes" value="${esc(F.nome)}" aria-label="Franquia" placeholder="Nome da franquia"><datalist id="frNomes">${F.nomes.map(n=>`<option value="${esc(n)}">`).join('')}</datalist>
  <button class="btn-ghost" data-fr="salvar">Salvar</button>${F.manual?'<button class="btn-ghost" data-fr="auto">Automático</button>':''}<button class="btn-ghost" data-fr="cancelar">Cancelar</button></div>
  <div class="fx-vazio" style="margin-top:4px">Escolha uma franquia que já existe para juntar, ou digite um nome novo para separar.</div>`;}
/* painel 3: preço em todas as lojas (tabela na largura toda) e, embaixo, as formas de comprar */
function fxLojas(){
  const g=MJ.gg;let s='';
  const vende=MJ.lojas.filter(l=>l.vende).sort((x,y)=>x.atual-y.atual),b=vende[0];
  // uma linha por loja: nome (e "alerta" se é uma das suas), desconto, preço de agora, quanto a mais que a mais barata, menor registrado
  const linha=(cls,n,url,tag,pc,ag,dif,menor)=>`<tr${cls?` class="${cls}"`:''}><td class="t">${url?`<a href="${esc(url)}" target="_blank" rel="noopener">${esc(n)}</a>`:esc(n)}${tag?`<span class="tag">${tag}</span>`:''}</td>
    <td class="n">${pc}</td><td class="n ag">${ag}</td><td class="n dif">${dif}</td><td class="n">${menor}</td></tr>`;
  const dif=v=>!b||v==null?'':v===b.atual?'a mais barata':v<b.atual?brl(b.atual-v)+' a menos':'+'+brl(v-b.atual);
  const rows=vende.map((l,i)=>linha(i?'':'melhor',l.loja,l.url,l.marcada?'alerta':'',l.corte>0?`<span class="pc">-${l.corte}%</span>`:'',brl(l.atual),dif(l.atual),l.menor!=null?brl(l.menor):'—'))
    .concat(g&&g.keyshop!=null?[linha('','Keyshop (GG.deals)',g.url,'chave','',brl(g.keyshop),dif(g.keyshop),g.hist_keyshop!=null?brl(g.hist_keyshop):'—')]:[])
    .concat(MJ.lojas.filter(l=>!l.vende).map(l=>linha('off',l.loja,l.url,'','',l.sem_atual?'—':'não vende','',l.menor!=null?brl(l.menor):'—')));
  s+=rows.length?`<div class="fx-cx"><h3>Preço agora por loja</h3><div class="ctab-wrap"><table class="ctab fx-lj tnum"><thead><tr><th>Loja</th><th class="n">Desconto</th><th class="n">Agora</th><th class="n">Diferença</th><th class="n">Menor registrado</th></tr></thead><tbody>${rows.join('')}</tbody></table></div></div>`
    :'<div class="fx-vazio">Nenhuma loja com preço para este jogo.</div>';
  const cm=fxCaminhos();return cm?`${s}<div class="fx-cx">${cm}</div>`:s;
}
/* painel 5: sobre o jogo (HowLongToBeat, notas, detalhes, DLCs) */
function fxSobre(){
  const j=MJ.jogo,a=MX&&MX.aug,lj=MX&&MX.loja,F=MJ.franquia;let s='';
  const h=a&&a.hltb;let hl;
  if(h){const vs=[h.story,h.extras,h.complete],m=Math.max(...vs.map(v=>v||0)),pc=v=>Math.min(100,(v||0)/m*100),jg=MJ.tenho&&MJ.jogado&&MJ.jogado.minutos;
    const cores=['#ff4757','#ff475788','#ffffff30'],nomes=['História principal','Principal + extras','Completacionista'];
    hl=`<div class="fx-linha">${[2,1,0].map(k=>vs[k]?`<i style="width:${pc(vs[k])}%;background:${cores[k]}"></i>`:'').join('')}${jg?`<i style="width:${pc(jg)}%;background:#ff4757;top:2px;bottom:2px"></i><span class="voce" style="left:${Math.min(94,Math.max(6,pc(jg)))}%">você ${horas(jg)}</span>`:''}</div>
      ${nomes.map((n,k)=>`<div class="fx-l"><span><i style="display:inline-block;width:9px;height:9px;margin-right:7px;background:${cores[k]}"></i>${n}</span><span>${horas(vs[k])}</span></div>`).join('')}
      ${a.hltb_url?`<div style="display:flex;justify-content:space-between;font-size:12px;margin-top:8px"><span class="fx-vazio">dados do HowLongToBeat</span><a href="${esc(a.hltb_url)}" target="_blank" rel="noopener">Mais informações ↗</a></div>`:''}`;
  }else hl=`<div class="fx-vazio">${fxBusca('Buscando no HowLongToBeat…','Sem dados do HowLongToBeat para este jogo.')}</div>`;
  s+=`<div class="fx-cx"><h3>How Long to Beat</h3>${hl}</div>`;
  const nota=(v,t,u)=>v==null?'':u?`<a href="${esc(u)}" target="_blank" rel="noopener"><b>${v}</b>${t}</a>`:`<span><b>${v}</b>${t}</span>`;
  if(a&&(a.meta!=null||a.oc!=null||a.jogando!=null))s+=`<div class="fx-cx"><div class="fx-crit">${nota(a.meta,'Metacritic (usuários)',a.meta_url)}${nota(a.oc,'OpenCritic',a.oc_url)}${a.jogando!=null?nota(fmtN(a.jogando),'jogando agora'):''}</div>
    ${a.pico?`<div class="fx-vazio" style="margin-top:8px">Pico de jogadores: ${fmtN(a.pico)}${a.pico_hoje?` · hoje ${fmtN(a.pico_hoje)}`:''}</div>`:''}</div>`;
  s+=`<div class="fx-cx"><dl class="fx-kv"><dt>Análises</dt><dd>${j.rcount?`<span class="${revClass(j.rpos,j.rcount)}">${esc(j.rotulo||'')}</span> · ${j.rpos}% de ${fmtN(j.rcount)}`:'—'}</dd>
    ${j.lancamento?`<dt>Lançamento</dt><dd>${fmtUnix(j.lancamento)}</dd>`:''}${lj&&lj.desenvolvedor?`<dt>Desenvolvedor</dt><dd>${esc(lj.desenvolvedor)}</dd>`:''}
    ${lj&&lj.editora&&lj.editora!==lj.desenvolvedor?`<dt>Editora</dt><dd>${esc(lj.editora)}</dd>`:''}${lj&&lj.generos?`<dt>Gêneros</dt><dd>${esc(lj.generos)}</dd>`:''}
    ${F?`<dt>Franquia</dt><dd>${esc(F.nome)}${F.manual?' <span class="fx-vazio">(trocada por você)</span>':''} · <a href="#" data-trocar>trocar</a>${MTROCA?fxTroca(F):''}</dd>`:''}</dl></div>`;
  return `<div class="fx-2c">${s}</div>${fxDlcs()}`;
}
/* os painéis da ficha: caixas na largura da ficha, uma aberta por vez (clique ou teclas ⇧1–⇧5); o escolhido vale para a próxima ficha */
let MABA='vale';
function fxListaAbas(){
  const j=MJ.jogo,o=MJ.item||IDX.get(j.appid)||{},F=MJ.franquia,a=MX&&MX.aug,h=a&&a.hltb,c=MX&&MX.conq,v=MOP.vered;
  const vende=MJ.lojas.filter(l=>l.vende).sort((x,y)=>x.atual-y.atual),b=vende.find(l=>l.marcada)||vende[0],ns=Object.keys(MJ.historico).length;
  const vale=MJ.tenho?(c&&c.total?`${c.feitas} de ${c.total} conquistas`:MJ.dlcs.length?`DLCs: tenho ${MJ.dlcs.filter(d=>d.tenho).length} de ${MJ.dlcs.length}`:'conquistas e DLCs')
    :v?v.rot+(v.sub?' · '+v.sub:''):MJ.selo?'Selo Kurokami':MJ.corte>0?(TITULO_TIPO[MJ.tipo_oferta]||`-${MJ.corte}% agora`):'sem promoção agora';
  return [['vale',MJ.tenho?'Seu progresso':'Vale a pena?',vale],
    ['hist','Histórico de preços',o.pisos&&o.pisos.sempre!=null?'menor de sempre '+brl(o.pisos.sempre):ns?`${ns} ${ns>1?'lojas':'loja'}`:'sem histórico'],
    ['lojas','Preço em todas as lojas',b?`${vende.length} ${vende.length>1?'lojas':'loja'} · ${brl(b.atual)} na ${b.loja}`:'nenhuma vende agora'],
    F&&F.total>=2?['fr','Franquia',`${F.nome} · tenho ${F.tenho} de ${F.total}`]:null,
    ['sobre','Sobre o jogo',[h&&h.story?horas(h.story)+' para zerar':'',MJ.dlcs.length?MJ.dlcs.length+' DLCs':''].filter(Boolean).join(' · ')||'notas e detalhes']].filter(Boolean);
}
function fxAbas(){const L=fxListaAbas();if(!L.some(a=>a[0]===MABA))MABA=L[0][0];
  return `<div class="fx-abas" role="tablist" aria-label="Partes da ficha">${L.map(([k,t,r],i)=>`<button class="fx-aba" role="tab" data-aba="${k}" aria-selected="${k===MABA}" title="Atalho: tecla ${i+1}"><i class="k">${i+1}</i><b>${esc(t)}</b><span>${esc(r)}</span></button>`).join('')}</div>`;}
const fxPainel=()=>({vale:fxVale,hist:fxHist,lojas:fxLojas,fr:fxFileira,sobre:fxSobre})[MABA]();
function fxAba(k){MABA=k;$$('#mbody .fx-aba').forEach(b=>b.setAttribute('aria-selected',b.dataset.aba===k));
  const p=$('#fxPainel');p.innerHTML=fxPainel();p.scrollTop=0;if($('#chart'))desenharGrafico();fxTrilho();}
function renderModal(){
  const j=MJ.jogo,lj=MX&&MX.loja,rol=$('#fxPainel')?$('#fxPainel').scrollTop:0,digitado=$('#frNome')&&$('#frNome').value,aberta=$('#mbody .fx-desc.aberta');
  const nome=SEM_LOGO.has(j.appid)?`<h2 class="fx-nome">${esc(j.nome)}</h2>`
    :`<img class="fx-logo" src="${CDNA}${j.appid}/logo.png" alt="${esc(j.nome)}" onerror="SEM_LOGO.add(${j.appid});this.hidden=true;this.nextElementSibling.hidden=false"><h2 class="fx-nome" hidden>${esc(j.nome)}</h2>`;
  $('#mbody').innerHTML=`<div class="fx-fundo" id="fxFundo"></div>
    <div class="fx-cab">${imgV(j,'fx-vert')}<div class="fx-info">${nome}${fxChips()}
      ${lj&&lj.descricao?`<p class="fx-desc">${esc(lj.descricao)}</p><button class="fx-mais" data-mais hidden>mais</button>`:''}${fxTiles()}${fxAcoes()}</div></div>
    ${fxAbas()}<div class="fx-painel" id="fxPainel" role="tabpanel">${fxPainel()}</div>`;
  if(digitado!=null&&$('#frNome'))$('#frNome').value=digitado;
  if(aberta&&$('#mbody .fx-desc')){$('#mbody .fx-desc').classList.add('aberta');$('#mbody .fx-mais').textContent='menos';}
  if($('#chart'))desenharGrafico();
  posFicha();$('#fxPainel').scrollTop=rol;
}
function fxChips(){const o=MJ.item||IDX.get(MJ.jogo.appid)||{};
  return `<div class="fx-chips">${MJ.tenho?'<span class="fx-chip tenho">✓ Na sua biblioteca</span>':''}${MJ.na_lista?'<span class="fx-chip lista">♥ Na lista de desejos</span>':''}${seloBadge(MJ)}${flags(Object.assign({},o,{selo:false}))}</div>`;}
function posFicha(){
  const f=$('#fxFundo'),a=MJ.jogo.appid,ss=MX&&MX.loja&&MX.loja.captura;
  const pinta=c=>{f.classList.add('cor');f.style.background=`radial-gradient(120% 90% at 15% 0%,${c} 0%,#000000 75%)`;};
  if(ss)f.style.backgroundImage=`url("${ss}")`;
  else if(MX!==undefined){if(MFUNDO[a])pinta(MFUNDO[a]);else corDaCapa(capaV(MJ.jogo)).then(c=>{MFUNDO[a]=c;if(MJ&&MJ.jogo.appid===a&&$('#fxFundo')===f)pinta(c);});}
  fxTrilho();
}
function fxTrilho(){   // franquia: o jogo atual no meio da fileira
  const t=$('#mbody .fx-trilho'),at=t&&t.querySelector('.atual');
  if(at){t.style.scrollBehavior='auto';t.scrollLeft=at.offsetLeft-t.offsetLeft-t.clientWidth/2+at.clientWidth/2;t.style.scrollBehavior='';}
  if(t)t.addEventListener('scroll',fxMedir,{passive:true});
  fxMedir();
}
function fxMedir(){   // "mais" só se a descrição não coube; setas só onde dá para rolar
  const d=$('#mbody .fx-desc'),m=$('#mbody .fx-mais');if(d&&m&&!d.classList.contains('aberta'))m.hidden=d.scrollHeight<=d.clientHeight+2;
  const t=$('#mbody .fx-trilho');if(!t)return;
  $('#mbody .fx-seta.e').hidden=t.scrollLeft<4;$('#mbody .fx-seta.d').hidden=t.scrollLeft+t.clientWidth>=t.scrollWidth-4;
}
addEventListener('resize',()=>{if(MJ&&!$('#modal').hidden){fxMedir();if($('#chart'))desenharGrafico();}});
$('#mbody').addEventListener('click',async e=>{
  const ab=e.target.closest('[data-aba]');if(ab){fxAba(ab.dataset.aba);return;}
  const fc=e.target.closest('[data-ficha]');if(fc){e.preventDefault();abrirJogo(+fc.dataset.ficha);return;}
  const ca=e.target.closest('[data-car]');if(ca){const t=$('#mbody .fx-trilho');t.scrollBy({left:+ca.dataset.car*t.clientWidth*.8});return;}
  const ma=e.target.closest('[data-mais]');if(ma){const d=$('#mbody .fx-desc');d.classList.toggle('aberta');ma.textContent=d.classList.contains('aberta')?'menos':'mais';return;}
  const tr=e.target.closest('[data-trocar]');if(tr){e.preventDefault();MTROCA=!MTROCA;renderModal();if(MTROCA)$('#frNome').focus();return;}
  const fr=e.target.closest('[data-fr]');if(fr){if(fr.dataset.fr==='cancelar'){MTROCA=false;renderModal();return;}
    const nome=fr.dataset.fr==='auto'?'':$('#frNome').value.trim();if(!nome&&fr.dataset.fr==='salvar'){toast('Digite o nome da franquia');return;}
    if((await post('/api/franquia',{appid:MJ.jogo.appid,nome})).ok===false)return;
    MTROCA=false;toast(nome?'Franquia: '+nome:'Franquia automática de volta');try{MJ=await api('/api/jogo?appid='+MJ.jogo.appid);}catch(_){}renderModal();return;}
  const r=e.target.closest('[data-range]');if(r){MRANGE=+r.dataset.range;renderModal();return;}
  const l=e.target.closest('[data-vista]');if(l){fxVista(l.dataset.vista);return;}
  const th=e.target.closest('[data-tenho]');if(th){if(MJ.tenho&&!MJ.tenho_manual){toast('Já está na sua biblioteca da Steam');return;}const novo=!MJ.tenho_manual;await post('/api/tenho',{appid:MJ.jogo.appid,tenho:novo});
    toast(novo?'Marcado como seu: sai dos alertas e do carrinho':'Desmarcado');MJ=await api('/api/jogo?appid='+MJ.jogo.appid);renderModal();FR.bib.velho=FR.vale.velho=true;return;}
  const mu=e.target.closest('[data-mudo]');if(mu){await post('/api/silenciar',{appid:MJ.jogo.appid,mudo:mu.dataset.mudo==='1'});toast(mu.dataset.mudo==='1'?'Sem alertas para este jogo':'Alertas de volta');
    MJ.mudo=mu.dataset.mudo==='1';const it=IDX.get(MJ.jogo.appid);if(it)it.mudo=MJ.mudo;renderModal();return;}
  const ml=e.target.closest('[data-mloja]');if(ml&&!ml.dataset.mcart){abrirNaLoja(MJ.jogo.appid,ml.dataset.mloja);return;}
  const mc=e.target.closest('[data-mcart]');if(mc){await alternarCarr(+mc.dataset.mcart);renderModal();return;}
  const mo=e.target.closest('[data-monitorar]');if(mo){if(mo.disabled)return;mo.disabled=true;await post('/api/extra',{appid:+mo.dataset.monitorar});mo.textContent='Monitorado';toast('Monitorado: entra na sua lista na próxima checagem');return;}
  const dm=e.target.closest('[data-desmonitorar]');if(dm){await post('/api/extra',{appid:+dm.dataset.desmonitorar,remover:true});toast('Não é mais monitorado (sai da lista na próxima checagem)');return;}
  const m=e.target.closest('[data-modo]');if(m){await post('/api/modo',{appid:MJ.jogo.appid,modo:m.dataset.modo});toast('Modo salvo: vale a partir da próxima checagem');MJ.modo=m.dataset.modo;
    const it=IDX.get(MJ.jogo.appid);if(it)it.modo=m.dataset.modo;renderModal();}
});
$('#mbody').addEventListener('change',async e=>{const s=e.target.closest('[data-dlc]');if(!s)return;
  await post('/api/dlc',{appid:+s.dataset.dlc,classe:s.value});toast('Classificação salva');MJ=await api('/api/jogo?appid='+MJ.jogo.appid);renderModal();});
/* o gráfico da ficha: uma linha só com o melhor preço de cada dia (degraus por baixo de todas as lojas que alertam);
   a linha cinza soma as outras lojas e a keyshop. Desenhado no tamanho real da caixa (sem esticar letras). */
const tolP=v=>Math.max(10,v*.01), DIA_MS=864e5;
const fmtMes=t=>new Date(t).toLocaleDateString('pt-BR',{month:'short',year:'2-digit'}).replace('.','');
function fxMarcadas(){const m=new Set(MJ.lojas.filter(l=>l.marcada).map(l=>l.loja));if(m.has('Steam'))m.add('Steam (direto)');return m;}
function fxSeries(filtro){   // [[loja, [[t, preço]...]]] sem o pacote completo e sem brinde (R$ 0)
  return Object.entries(MJ.historico).filter(([n])=>n!=='Completo (Steam)'&&filtro(n))
    .map(([n,p])=>[n,p.map(x=>[Date.parse(x[0]),x[1]]).filter(x=>x[1]>0).sort((a,b)=>a[0]-b[0])]).filter(([,p])=>p.length);}
function fxEnvelope(series){   // degraus [início, preço, loja]: o menor preço valendo em cada momento
  const ts=[...new Set(series.flatMap(([,p])=>p.map(x=>x[0])))].sort((a,b)=>a-b),ix=series.map(()=>-1),out=[];
  for(const t of ts){let v=null,lj=null;
    series.forEach(([n,p],k)=>{while(ix[k]+1<p.length&&p[ix[k]+1][0]<=t)ix[k]++;if(ix[k]>=0&&(v==null||p[ix[k]][1]<v)){v=p[ix[k]][1];lj=n;}});
    const u=out[out.length-1];if(!u||u[1]!==v||u[2]!==lj)out.push([t,v,lj]);}
  return out;}
function fxEnvMarc(){const m=fxMarcadas(),s=fxSeries(n=>m.has(n));return s.length?{env:fxEnvelope(s),marc:true}:{env:fxEnvelope(fxSeries(()=>true)),marc:false};}
const ehSteam=n=>n==='Steam'||n==='Steam (direto)';
function fxVista(v){if(!MJ||!$('#chart'))return;if(v==='steam'&&!fxSeries(ehSteam).length)return;MVISTA=v;desenharGrafico();}
const noTempo=(env,t)=>{let r=null;for(const x of env){if(x[0]>t)break;r=x;}return r;};
function recorta(env,t0){const a=noTempo(env,t0);return (a?[[t0,a[1],a[2]]]:[]).concat(env.filter(x=>x[0]>t0));}
function desenharGrafico(){
  const box=$('#chart'),leg=$('#legend');if(!box)return;
  const agora=Date.now(),temSteam=fxSeries(ehSteam).length>0;if(!temSteam)MVISTA='todas';
  const steam=MVISTA==='steam',em=fxEnvelope(fxSeries(steam?ehSteam:()=>true));
  if(!em.length){box.innerHTML='<div class="empty" style="padding:30px">Sem histórico de preços.</div>';leg.innerHTML='';$('#faixa').innerHTML='';return;}
  const t0=MRANGE>=99999?em[0][0]:agora-MRANGE*DIA_MS;
  const A=recorta(em,t0);
  const o=MJ.item||IDX.get(MJ.jogo.appid)||{},cheio=(MJ.lojas.find(l=>l.loja===(steam?'Steam':o.loja))||MJ.lojas.find(l=>l.loja===o.loja)||{}).cheio||MJ.jogo.cheio_steam;
  leg.innerHTML=`<span class="seg" role="group" aria-label="Lojas do gráfico">${temSteam?`<button data-vista="steam" aria-pressed="${steam}">Steam</button>`:''}<button data-vista="todas" aria-pressed="${!steam}" title="O menor preço entre todas as lojas e a keyshop, dia a dia">Todas as lojas</button></span>
    <span style="color:var(--dim)">${temSteam?'<kbd>T</kbd> ou arraste para o lado: ':''}${steam?'só o preço da Steam':'o menor preço entre as lojas, com a loja no hover'}</span>${cheio?'<span><i class="tr"></i>Preço cheio</span>':''}`;
  if(!A.length){box.innerHTML='<div class="empty" style="padding:30px">Sem dados no período.</div>';fxFaixa(t0,agora);return;}
  const W=Math.max(320,box.clientWidth-16),H=Math.round(innerWidth>820?Math.min(300,Math.max(180,innerHeight-700)):200),PL=58,PR=14,PT=14,PB=24;
  const vis=A,maxY=Math.max(cheio||0,...vis.map(x=>x[1]))*1.1||100;
  const X=t=>PL+(t-t0)/(agora-t0)*(W-PL-PR),Y=v=>PT+(1-v/maxY)*(H-PT-PB);
  const degraus=E=>E.map((x,i)=>(i?`H${X(x[0]).toFixed(1)}V`:`M${X(x[0]).toFixed(1)},`)+Y(x[1]).toFixed(1)).join('')+`H${X(agora).toFixed(1)}`;
  let g='';for(let i=0;i<=4;i++){const v=maxY*i/4;g+=`<line x1="${PL}" x2="${W-PR}" y1="${Y(v)}" y2="${Y(v)}" stroke="#ffffff12"/><text x="${PL-8}" y="${Y(v)+4}" fill="#979797" font-size="11" text-anchor="end">${brl0(v)}</text>`;}
  for(let i=0;i<=4;i++){const t=t0+(agora-t0)*i/4;g+=`<text x="${X(t)}" y="${H-6}" fill="#979797" font-size="11" text-anchor="${i===0?'start':i===4?'end':'middle'}">${fmtMes(t)}</text>`;}
  if(cheio&&cheio<maxY)g+=`<line x1="${PL}" x2="${W-PR}" y1="${Y(cheio)}" y2="${Y(cheio)}" stroke="#8c8c8c" stroke-dasharray="4 4"/><text x="${W-PR}" y="${Y(cheio)-5}" fill="#979797" font-size="11" text-anchor="end">cheio ${brl(cheio)}</text>`;
  const dA=degraus(A),hoje=A[A.length-1][1],mn=A.reduce((m,x)=>x[1]<m[1]?x:m,A[0]);
  const lbl=(x,y,t,ancora)=>`<text x="${x}" y="${y}" fill="#fff" font-size="12" text-anchor="${ancora}" paint-order="stroke" stroke="#000" stroke-width="3">${t}</text>`;
  const ehHoje=Math.abs(mn[1]-hoje)<=tolP(hoje);
  const marcas=`<circle cx="${X(agora)}" cy="${Y(hoje)}" r="4.5" fill="#ff4757"/>${lbl(X(agora)-8,Y(hoje)-9,'hoje '+brl(hoje)+(ehHoje?' · o menor do período':''),'end')}`
    +(ehHoje?'':`<circle cx="${X(Math.max(mn[0],t0))}" cy="${Y(mn[1])}" r="3.5" fill="#fff"/>${lbl(Math.min(X(Math.max(mn[0],t0))+8,W-PR-150),Y(mn[1])+16,'menor do período '+brl(mn[1]),'start')}`);
  box.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${g}<path d="${dA}V${Y(0)}H${X(A[0][0])}Z" fill="#ff475714"/>
<path d="${dA}" fill="none" stroke="#ff4757" stroke-width="2.2"/>${marcas}
    <line id="cur" y1="${PT}" y2="${H-PB}" stroke="#ffffff66" visibility="hidden"/><rect x="${PL}" y="0" width="${W-PL-PR}" height="${H}" fill="transparent"/></svg><div class="tip" id="tip"></div>`;
  const svg=box.querySelector('svg'),tip=$('#tip'),cur=box.querySelector('#cur');
  svg.addEventListener('mousemove',e=>{const r=svg.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*W;if(x<PL){tip.style.display='none';return;}
    const t=t0+(x-PL)/(W-PL-PR)*(agora-t0),a=noTempo(A,t);cur.setAttribute('x1',x);cur.setAttribute('x2',x);cur.setAttribute('visibility','visible');
    const pc=v=>cheio&&v<cheio?` <span class="pc">-${Math.round((1-v/cheio)*100)}%</span>`:'';
    tip.innerHTML=`<div style="margin-bottom:3px"><b>${new Date(t).toLocaleDateString('pt-BR')}</b></div>${a?`<div><span style="color:#d63031">■</span> <b>${brl(a[1])}</b>${pc(a[1])} ${steam?'':'na '+esc(a[2])}</div>`:''}`;
    tip.style.display='block';const px=e.clientX-box.getBoundingClientRect().left;tip.style.left=Math.min(px+12,box.clientWidth-tip.offsetWidth-4)+'px';tip.style.top='12px';});
  svg.addEventListener('mouseleave',()=>{tip.style.display='none';cur.setAttribute('visibility','hidden');});
  if(temSteam)svg.addEventListener('pointerdown',ev=>{const x0=ev.clientX;   // arrastar o gráfico para o lado (dedo ou mouse) troca entre Steam e todas as lojas
    addEventListener('pointerup',up=>{if(Math.abs(up.clientX-x0)>70)fxVista(MVISTA==='steam'?'todas':'steam');},{once:true});});
  fxFaixa(t0,agora);
}
/* faixa de promoções: uma linha por loja, um quadrado por mês (por semana em 3 meses), na cor do maior desconto */
function fxFaixa(t0,agora){
  const el=$('#faixa');if(!el)return;const m=fxMarcadas();
  const S=fxSeries(n=>!/^GG\.deals/.test(n)&&!(n==='Steam (direto)'&&MJ.historico.Steam)&&(MVISTA!=='steam'||ehSteam(n)))
    .sort((a,b)=>(m.has(b[0])-m.has(a[0]))||a[0].localeCompare(b[0]));
  const C=[];   // colunas [início, fim, rótulo]
  if(agora-t0<=100*DIA_MS)for(let a=t0;a<agora;a+=7*DIA_MS)C.push([a,Math.min(a+7*DIA_MS,agora),new Date(a).toLocaleDateString('pt-BR',{day:'numeric',month:'short'}).replace('.','')]);
  else{const d=new Date(t0);d.setDate(1);d.setHours(0,0,0,0);
    while(d.getTime()<agora){const a=d.getTime();d.setMonth(d.getMonth()+1);C.push([Math.max(a,t0),Math.min(d.getTime(),agora),fmtMes(a)]);}}
  const linhas=S.map(([n,p])=>{const cheio=Math.max(...p.map(x=>x[1]));
    const cel=C.map(([a,b,r])=>{let v=null;p.forEach((x,i)=>{const f=i+1<p.length?p[i+1][0]:agora;if(x[0]<b&&f>a&&(v==null||x[1]<v))v=x[1];});
      if(v==null)return '<i class="v"></i>';const pc=Math.round((1-v/cheio)*100);
      return pc<5?`<i title="${esc(n)} · ${r}: sem promoção (${brl(v)})"></i>`:`<i data-calor="${calorDe(pc)}" title="${esc(n)} · ${r}: até -${pc}% (${brl(v)})"></i>`;});
    return cel.some(c=>c!=='<i class="v"></i>')?`<span class="ff-l${m.has(n)?' m':''}" title="${esc(n)}">${esc(n)}</span>${cel.join('')}`:'';}).filter(Boolean);
  if(!linhas.length){el.innerHTML='';return;}
  const k=Math.ceil(C.length/7);
  el.innerHTML=`<h3>Promoções por loja <span class="q">${C.length>16?'um quadrado por mês':'um quadrado por '+(agora-t0<=100*DIA_MS?'semana':'mês')} · passe o mouse para ver o preço</span></h3>
    <div class="ff" style="--n:${C.length}">${linhas.join('')}<span></span>${C.map((c,i)=>`<span class="ff-x">${i%k?'':c[2]}</span>`).join('')}</div>
    <div class="ff-leg"><span><i></i>sem promoção</span><span><i data-calor="0"></i>até -49%</span><span><i data-calor="1"></i>-50%</span><span><i data-calor="2"></i>-75%</span><span><i data-calor="3"></i>-90% ou mais</span><span class="fx-vazio">${so?'só as lojas que alertam (as outras em "Outras lojas e keyshop")':'loja em branco = alerta'}</span></div>`;
}

