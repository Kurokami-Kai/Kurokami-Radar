/* ================= Status > Progresso: o que você realmente jogou (dados de /api/progresso, radar/jogados.py) ================= */
let JG=null;
const PG_ESTADOS=[['platina','Platinados','todas as conquistas'],['andamento','Em andamento','algumas conquistas'],['zero','0% de conquistas','contam como não jogados'],
  ['sem','Sem conquistas','jogados; só as horas dizem'],['nunca','Nunca jogados','0 minutos'],['pendente','Lendo conquistas','a Steam ainda não respondeu']];
const PG_COR={platina:'var(--sinal)',andamento:'#8a1520',zero:'#4a1016',sem:'#7f7f7f',nunca:'#2a2a2a',pendente:'#454545'};
const fmtH=m=>{const h=m/60;return h<1?(m?'<1 h':'0 h'):(h<10?h.toFixed(1).replace('.',','):Math.round(h).toLocaleString('pt-BR'))+' h';};
const pgJogou=j=>j.estado==='platina'||j.estado==='andamento'||j.estado==='sem'||j.estado==='pendente'||(j.estado==='zero'&&!!S.pgZero);
async function renderJogados(){
  if(!JG)$('#progCorpo').innerHTML='<div class="empty">Lendo a biblioteca…</div>';
  try{JG=await api('/api/progresso');}catch(e){$('#progCorpo').innerHTML='<div class="empty">Não consegui ler o progresso agora.</div>';return;}
  desenharJogados();}
function pgColunas(itens){const mx=Math.max(1,...itens.map(i=>i.n));
  return `<div class="pg-cols">${itens.map(i=>`<div class="pg-col" title="${esc(i.tip||'')}"><span class="pg-cn tnum">${fmtN(i.n)}</span><span class="pg-cb"><i style="height:${Math.max(i.n?3:0,Math.round(i.n/mx*100))}%"></i></span><span class="pg-cr">${esc(i.rot)}</span></div>`).join('')}</div>`;}
function pgLinha(j){const pct=j.total?Math.round(j.feitas/j.total*100):0;
  return `<div class="pg-row" data-open="${j.appid}">${art(j.appid,j.nome,j.capa)}<div class="pg-n"><span class="pg-nome">${esc(j.nome)}</span>
    <span class="pg-sub">${j.estado==='nunca'?'nunca jogado':fmtH(j.minutos)+' jogadas'+(j.ultima?' · última vez em '+new Date(j.ultima*1000).toLocaleDateString('pt-BR',{month:'2-digit',year:'numeric'}):'')}</span></div>
    <div class="pg-conq">${j.total?`<span class="pg-bar"><i style="width:${pct}%;background:${PG_COR[j.estado]}"></i></span><span class="tnum">${j.feitas}/${j.total} · ${pct}%</span>`:`<span class="pg-sub">${j.estado==='pendente'?'lendo conquistas…':j.estado==='nunca'?'':'sem conquistas'}</span>`}</div></div>`;}
function desenharJogados(){
  const J=JG.jogos,box=$('#progCorpo');
  if(!J.length){box.innerHTML='<div class="empty">Ainda não li o tempo jogado. Entre com a Steam e coloque a chave da Steam em Configurações; a biblioteca é lida uma vez por dia, em segundo plano.</div>';return;}
  const por={};PG_ESTADOS.forEach(([k])=>por[k]=[]);J.forEach(j=>por[j.estado].push(j));
  const jogados=J.filter(pgJogou),horas=jogados.reduce((s,j)=>s+j.minutos,0),zeroH=por.zero.reduce((s,j)=>s+j.minutos,0);
  const f=PG_ESTADOS.some(([k])=>k===S.pgLista)?S.pgLista:'platina';
  const kpi=(n,t,s)=>`<div class="pg-kpi"><b class="tnum">${n}</b><span>${t}</span>${s?`<small>${s}</small>`:''}</div>`;
  const faixas=[['< 1 h',0,60],['1–5 h',60,300],['5–20 h',300,1200],['20–50 h',1200,3000],['50–100 h',3000,6000],['100 h +',6000,1e12]];
  const hist=faixas.map(([rot,a,b])=>({rot,n:jogados.filter(j=>j.minutos>=a&&j.minutos<b).length,tip:rot}));
  const anos={};jogados.forEach(j=>{if(j.ultima){const a=new Date(j.ultima*1000).getFullYear();anos[a]=(anos[a]||0)+1;}});
  const ay=Object.keys(anos).map(Number).sort((a,b)=>a-b),a0=ay.length?ay[0]:0,a1=new Date().getFullYear();
  const porAno=[];for(let a=a0;a&&a<=a1;a++)porAno.push({rot:String(a),n:anos[a]||0,tip:'jogos cuja última vez foi em '+a});
  const top=[...jogados].sort((a,b)=>b.minutos-a.minutos).slice(0,15),mx=top.length?top[0].minutos:1;
  const seg=PG_ESTADOS.filter(([k])=>por[k].length);
  const lista=[...por[f]].sort((a,b)=>f==='andamento'?(b.feitas/b.total-a.feitas/a.total)||b.minutos-a.minutos:f==='nunca'?a.nome.localeCompare(b.nome,'pt-BR'):b.minutos-a.minutos);
  const quantos=S.pgMais||40;
  box.innerHTML=`
   ${JG.pendentes?`<div class="pg-aviso">Lendo as conquistas de ${fmtN(JG.pendentes)} jogo${JG.pendentes>1?'s':''} em segundo plano (cerca de 60 a cada 3 minutos). Até lá eles contam como jogados, e os números abaixo ainda mudam.</div>`:''}
   <div class="pg-kpis">${kpi(fmtN(J.length),'jogos na biblioteca')}${kpi(fmtN(jogados.length),'realmente jogados',Math.round(jogados.length/J.length*100)+'% da biblioteca')}
     ${kpi(fmtN(por.platina.length),'platinados',por.platina.length+por.andamento.length?Math.round(por.platina.length/(por.platina.length+por.andamento.length)*100)+'% dos jogados que têm conquistas':'')}
     ${kpi(fmtN(Math.round(horas/60)),'horas jogadas',zeroH&&!S.pgZero?fmtN(Math.round(zeroH/60))+' h em jogos com 0% ficaram de fora':'')}
     ${kpi(fmtN(J.length-jogados.length),'não jogados',por.zero.length&&!S.pgZero?fmtN(por.nunca.length)+' sem horas + '+fmtN(por.zero.length)+' com 0% de conquistas':'sem nenhum minuto')}</div>
   <div class="pg-opc"><label><input type="checkbox" id="pgZero"${S.pgZero?' checked':''}> Contar os jogos com 0% de conquistas como jogados <small>(desligado: podem ser só farm de cartas ou jogo aberto sem jogar)</small></label></div>
   <h3 class="pg-h">Sua biblioteca por progresso</h3>
   <div class="pg-seg" role="img" aria-label="Biblioteca por progresso">${seg.map(([k,t])=>`<i style="flex:${por[k].length};background:${PG_COR[k]}" title="${t}: ${por[k].length}"></i>`).join('')}</div>
   <div class="pg-leg">${seg.map(([k,t,s])=>`<span><i style="background:${PG_COR[k]}"></i>${t} <b class="tnum">${fmtN(por[k].length)}</b><small>${s}</small></span>`).join('')}</div>
   <div class="pg-2">
     <div><h3 class="pg-h">Mais jogados</h3><div class="pg-top">${top.map(j=>`<div class="pg-t" data-open="${j.appid}"><span class="pg-tn">${esc(j.nome)}</span><span class="pg-tb"><i style="width:${Math.max(2,Math.round(j.minutos/mx*100))}%;background:${PG_COR[j.estado]}"></i></span><span class="pg-th tnum">${fmtH(j.minutos)}</span></div>`).join('')||'<div class="empty">Nada jogado ainda.</div>'}</div></div>
     <div><h3 class="pg-h">Quanto você joga cada jogo</h3>${pgColunas(hist)}
       <h3 class="pg-h">Última vez que jogou, por ano</h3>${porAno.length?pgColunas(porAno):'<div class="empty">Sem datas ainda.</div>'}</div>
   </div>
   <h3 class="pg-h">Jogo a jogo</h3>
   <div class="nf-bar"><div class="nf-seg">${PG_ESTADOS.filter(([k])=>por[k].length||k===f).map(([k,t])=>`<button type="button" data-pgl="${k}" aria-pressed="${f===k}">${t}<span>${fmtN(por[k].length)}</span></button>`).join('')}</div>
     <span class="nf-info">${esc(PG_ESTADOS.find(x=>x[0]===f)[2])}</span></div>
   <div class="pg-lista">${lista.slice(0,quantos).map(pgLinha).join('')||'<div class="empty">Nenhum jogo aqui.</div>'}</div>
   ${lista.length>quantos?`<div class="pg-mais"><button class="btn-ghost" type="button" data-pgmais>Mostrar mais (${fmtN(lista.length-quantos)})</button></div>`:''}`;
}
$('#tab-prog').addEventListener('click',e=>{const b=e.target.closest('[data-pgl]');if(b){S.pgLista=b.dataset.pgl;S.pgMais=40;save();desenharJogados();return;}
  if(e.target.closest('[data-pgmais]')){S.pgMais=(S.pgMais||40)+60;desenharJogados();return;}});
$('#tab-prog').addEventListener('change',e=>{if(e.target.id==='pgZero'){S.pgZero=e.target.checked;save();desenharJogados();}});
