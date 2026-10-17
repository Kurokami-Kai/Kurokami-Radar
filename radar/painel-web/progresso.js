/* ================= Status > Progresso: o que você realmente jogou (dados de /api/progresso, radar/jogados.py) =================
   Grupos: platina, andamento, semc (nenhuma conquista feita, tenha o jogo conquistas ou não), marcado (semc que você disse que jogou
   de verdade; só com o farm de cartas ligado), nunca, pendente. Com o farm de cartas ligado (Configurações → Jogos), semc não conta como jogado. */
let JG=null;
let PGD=null,pgA0=2022;const RP={};   // clique nos gráficos (fim do arquivo). PGD: {h: faixa} ou {ano, mes?}; RP: ano → /api/replay
const PG_ESTADOS=[['platina','Platinados','todas as conquistas'],['andamento','Em andamento','algumas conquistas'],['semc','Sem conquistas feitas','jogo sem conquistas ou com 0% feito'],
  ['marcado','Marcados como jogados','sem conquista, mas você jogou de verdade'],['nunca','Nunca jogados','0 minutos'],['pendente','Lendo conquistas','a Steam ainda não respondeu']];
const PG_COR={platina:'var(--sinal)',andamento:'#8a1520',semc:'#4a1016',marcado:'#9a9a9a',nunca:'#2a2a2a',pendente:'#454545'};
const fmtH=m=>{const h=m/60;return h<1?(m?'<1 h':'0 h'):(h<10?h.toFixed(1).replace('.',','):Math.round(h).toLocaleString('pt-BR'))+' h';};
const pgGrupo=j=>j.estado==='zero'||j.estado==='sem'?(JG.farm&&j.marcado?'marcado':'semc'):j.estado;
// pendente (conquistas ainda não lidas): com o farm ligado não dá para saber, então fica de fora de tudo até ser lido; desligado, horas bastam
const pgJogou=j=>{const g=pgGrupo(j);return g==='platina'||g==='andamento'||g==='marcado'||((g==='semc'||g==='pendente')&&!JG.farm);};
async function renderJogados(){
  renderMetas();
  if(!JG)$('#progCorpo').innerHTML='<div class="empty">Lendo a biblioteca…</div>';
  try{JG=await api('/api/progresso');}catch(e){$('#progCorpo').innerHTML='<div class="empty">Não consegui ler o progresso agora.</div>';return;}
  desenharJogados();clearTimeout(renderJogados.t);
  if(JG.pendentes&&JG.coletando&&S.tab==='prog')renderJogados.t=setTimeout(()=>{if(S.tab==='prog')renderJogados();},30000);}
function pgColunas(itens){const mx=Math.max(1,...itens.map(i=>i.n));
  return `<div class="pg-cols">${itens.map(i=>{const t=i.at?'button':'div';return `<${t}${i.at?' type="button" '+i.at+' aria-pressed="'+!!i.on+'"':''} class="pg-col" title="${esc(i.tip||'')}"><span class="pg-cn tnum">${i.txt!=null?i.txt:fmtN(i.n)}</span><span class="pg-cb"><i style="height:${Math.max(i.n?3:0,Math.round(i.n/mx*100))}%"></i></span><span class="pg-cr">${esc(i.rot)}</span></${t}>`;}).join('')}</div>`;}
const pgKpi=(n,t,s)=>`<div class="pg-kpi"><b class="tnum">${n}</b><span>${t}</span>${s?`<small>${s}</small>`:''}</div>`;
const PG_FAIXAS=[['< 1 h',0,60],['1–5 h',60,300],['5–20 h',300,1200],['20–50 h',1200,3000],['50–100 h',3000,6000],['100 h +',6000,1e12]];
function pgLinha(j){const pct=j.total?Math.round(j.feitas/j.total*100):0,g=pgGrupo(j);
  const btn=JG.farm&&(g==='semc'||g==='marcado')?`<button type="button" class="btn-ghost pg-j" data-pgj="${j.appid}" data-v="${g==='semc'?1:0}">${g==='semc'?'Joguei de verdade':'Desmarcar'}</button>`:'';
  return `<div class="pg-row" data-open="${j.appid}">${art(j.appid,j.nome,j.capa)}<div class="pg-n"><span class="pg-nome">${esc(j.nome)}</span>
    <span class="pg-sub">${g==='nunca'?'nunca jogado':fmtH(j.minutos)+' jogadas'+(j.ultima?' · última vez em '+new Date(j.ultima*1000).toLocaleDateString('pt-BR',{month:'2-digit',year:'numeric'}):'')}</span></div>
    <div class="pg-conq">${j.total?`<span class="pg-bar"><i style="width:${pct}%;background:${PG_COR[g]}"></i></span><span class="tnum">${j.feitas}/${j.total} · ${pct}%</span>`:`<span class="pg-sub">${g==='pendente'?'lendo conquistas…':g==='nunca'?'':'sem conquistas'}</span>`}${btn}</div></div>`;}
function desenharJogados(){
  const J=JG.jogos,box=$('#progCorpo');
  if(!J.length){box.innerHTML='<div class="empty">Ainda não li o tempo jogado. Entre com a Steam e coloque a chave da Steam em Configurações; a biblioteca é lida uma vez por dia, em segundo plano.</div>';return;}
  const por={};PG_ESTADOS.forEach(([k])=>por[k]=[]);J.forEach(j=>por[pgGrupo(j)].push(j));
  const jogados=J.filter(pgJogou),horas=jogados.reduce((s,j)=>s+j.minutos,0),foraH=JG.farm?por.semc.reduce((s,j)=>s+j.minutos,0):0;
  const f=PG_ESTADOS.some(([k])=>k===S.pgLista)?S.pgLista:'platina';
  const kpi=pgKpi;
  const hist=PG_FAIXAS.map(([rot,a,b],k)=>({rot,n:jogados.filter(j=>j.minutos>=a&&j.minutos<b).length,tip:'ver os jogos com '+rot,at:`data-pgh="${k}"`,on:PGD&&PGD.h===k}));
  const anos={};jogados.forEach(j=>{if(j.ultima){const a=new Date(j.ultima*1000).getFullYear();anos[a]=(anos[a]||0)+1;}});
  const ay=Object.keys(anos).map(Number).sort((a,b)=>a-b),a0=ay.length?ay[0]:0,a1=new Date().getFullYear();
  pgA0=Math.min(a0||a1,2022);
  const porAno=[];for(let a=a0;a&&a<=a1;a++)porAno.push({rot:String(a),n:anos[a]||0,tip:'jogos cuja última vez foi em '+a+' · clique para ver o ano jogo a jogo',at:`data-pgano="${a}"`,on:PGD&&PGD.ano===a});
  const top=[...jogados].sort((a,b)=>b.minutos-a.minutos).slice(0,15),mx=top.length?top[0].minutos:1;
  const seg=PG_ESTADOS.filter(([k])=>por[k].length);
  const sub=k=>k==='semc'?(JG.farm?'não contam como jogados (farm de cartas ligado)':'contam como jogados (farm de cartas desligado)'):PG_ESTADOS.find(x=>x[0]===k)[2];
  const lista=[...por[f]].sort((a,b)=>f==='andamento'?(b.feitas/b.total-a.feitas/a.total)||b.minutos-a.minutos:f==='nunca'?a.nome.localeCompare(b.nome,'pt-BR'):b.minutos-a.minutos);
  const quantos=S.pgMais||40;
  box.innerHTML=`
   ${JG.pendentes?(JG.coletando?`<div class="pg-aviso">Lendo as conquistas de ${fmtN(JG.pendentes)} jogo${JG.pendentes>1?'s':''} em segundo plano (cerca de 100 a cada 3 minutos). ${JG.farm?'Até lá eles ficam fora dos números e dos gráficos abaixo, que crescem conforme a leitura avança.':'Até lá eles contam como jogados.'} A tela se atualiza sozinha.</div>`
     :`<div class="pg-aviso">As conquistas de ${fmtN(JG.pendentes)} jogo${JG.pendentes>1?'s':''} ainda não foram lidas, e elas só são lidas com o Hunter rodando (ícone na bandeja do Windows). Só o painel aberto não lê nada.</div>`):''}
   <div class="pg-opc">${JG.farm?'<b>Farm de cartas ligado:</b> jogo sem nenhuma conquista feita conta como <b>não jogado</b>. Jogou de verdade? Em <i>Sem conquistas feitas</i>, use <i>Joguei de verdade</i>.'
     :'Usou programa de farm de cartas? Ligue para os jogos sem conquista contarem como <b>não jogados</b>.'} <a href="#" data-pgcfg>${JG.farm?'Desligar':'Ligar'} em Configurações ›</a></div>
   <div class="pg-kpis">${kpi(fmtN(J.length),'jogos na biblioteca')}${kpi(fmtN(jogados.length),'realmente jogados',Math.round(jogados.length/J.length*100)+'% da biblioteca'+(JG.farm&&por.pendente.length?' · sem contar '+fmtN(por.pendente.length)+' ainda sendo lidos':''))}
     ${kpi(fmtN(por.platina.length),'platinados',por.platina.length+por.andamento.length?Math.round(por.platina.length/(por.platina.length+por.andamento.length)*100)+'% dos jogados que têm conquistas':'')}
     ${kpi(fmtN(Math.round(horas/60)),'horas jogadas',foraH?fmtN(Math.round(foraH/60))+' h em jogos sem nenhuma conquista ficaram de fora':'')}
     ${kpi(fmtN(J.length-jogados.length-(JG.farm?por.pendente.length:0)),'não jogados',JG.farm&&por.semc.length?fmtN(por.nunca.length)+' sem horas + '+fmtN(por.semc.length)+' sem conquista feita':'sem nenhum minuto')}</div>
   <h3 class="pg-h">Sua biblioteca por progresso</h3>
   <div class="pg-seg" role="img" aria-label="Biblioteca por progresso">${seg.map(([k,t])=>`<i style="flex:${por[k].length};background:${PG_COR[k]}" title="${t}: ${por[k].length}"></i>`).join('')}</div>
   <div class="pg-leg">${seg.map(([k,t])=>`<span><i style="background:${PG_COR[k]}"></i>${t} <b class="tnum">${fmtN(por[k].length)}</b><small>${sub(k)}</small></span>`).join('')}</div>
   <div class="pg-2">
     <div><h3 class="pg-h">Mais jogados</h3><div class="pg-top">${top.map(j=>`<div class="pg-t" data-open="${j.appid}"><span class="pg-tn">${esc(j.nome)}</span><span class="pg-tb"><i style="width:${Math.max(2,Math.round(j.minutos/mx*100))}%;background:${PG_COR[pgGrupo(j)]}"></i></span><span class="pg-th tnum">${fmtH(j.minutos)}</span></div>`).join('')||'<div class="empty">Nada jogado ainda.</div>'}</div></div>
     <div><h3 class="pg-h">Quanto você joga cada jogo <small>clique numa coluna</small></h3>${pgColunas(hist)}
       <h3 class="pg-h">Última vez que jogou, por ano <small>clique num ano: ele jogo a jogo</small></h3>${porAno.length?pgColunas(porAno):'<div class="empty">Sem datas ainda.</div>'}</div>
   </div>
   <div id="pgDet">${PGD?pgDet():''}</div>
   <h3 class="pg-h">Jogo a jogo</h3>
   <div class="nf-bar"><div class="nf-seg">${PG_ESTADOS.filter(([k])=>por[k].length||k===f).map(([k,t])=>`<button type="button" data-pgl="${k}" aria-pressed="${f===k}">${t}<span>${fmtN(por[k].length)}</span></button>`).join('')}</div>
     <span class="nf-info">${esc(sub(f))}</span></div>
   <div class="pg-lista">${lista.slice(0,quantos).map(pgLinha).join('')||'<div class="empty">Nenhum jogo aqui.</div>'}</div>
   ${lista.length>quantos?`<div class="pg-mais"><button class="btn-ghost" type="button" data-pgmais>Mostrar mais (${fmtN(lista.length-quantos)})</button></div>`:''}`;
}
$('#tab-prog').addEventListener('click',async e=>{
  const an=e.target.closest('[data-pgano]');if(an){pgAbrir({ano:+an.dataset.pgano});return;}
  const fh=e.target.closest('[data-pgh]');if(fh){pgAbrir(PGD&&PGD.h===+fh.dataset.pgh?null:{h:+fh.dataset.pgh});return;}
  const ms=e.target.closest('[data-pgmes]');if(ms&&PGD){const m=+ms.dataset.pgmes;PGD.mes=PGD.mes===m?null:m;pgDesenharDet();return;}
  if(e.target.closest('[data-pgfechar]')){pgAbrir(null);return;}
  const j=e.target.closest('[data-pgj]');
  if(j){e.stopPropagation();const a=+j.dataset.pgj,v=j.dataset.v==='1',r=await post('/api/jogou',{appid:a,jogou:v});
    if(r&&r.ok){const x=JG.jogos.find(y=>y.appid===a);if(x)x.marcado=v;desenharJogados();}return;}
  if(e.target.closest('[data-pgcfg]')){e.preventDefault();ls.set('cfgSec','jogos');setTab('cfg');window.scrollTo(0,0);return;}
  const b=e.target.closest('[data-pgl]');if(b){S.pgLista=b.dataset.pgl;S.pgMais=40;save();desenharJogados();return;}
  if(e.target.closest('[data-pgmais]')){S.pgMais=(S.pgMais||40)+60;desenharJogados();return;}});

/* ---- Clique nos gráficos: uma faixa de horas, ou um ano jogo a jogo como o Steam Replay (/api/replay, radar/replay.py).
   Com o farm de cartas ligado, o servidor já tira os jogos de farm do Replay; o resto da aba usa pgJogou. ---- */
const PG_MES=['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
const pgCapa=g=>g.capa||`https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/${g.appid}/header.jpg`;
const fmtS=s=>s<3600?Math.max(1,Math.round(s/60))+' min':fmtH(Math.round(s/60));
const pgMesAno=t=>new Date(t*1000).toLocaleDateString('pt-BR',{month:'2-digit',year:'numeric'});
function pgAbrir(d){PGD=d;
  if(d&&d.ano&&(!RP[d.ano]||RP[d.ano].tentar)){delete RP[d.ano];api('/api/replay?ano='+d.ano).catch(()=>({ok:false,tentar:true,motivo:'Não consegui ler agora.'})).then(r=>{RP[d.ano]=r;if(PGD&&PGD.ano===d.ano)pgDesenharDet();});}
  pgDesenharDet(true);}
function pgDesenharDet(rolar){const box=$('#pgDet');if(!box)return;box.innerHTML=PGD?pgDet():'';
  $$('#progCorpo [data-pgano].pg-col').forEach(c=>c.setAttribute('aria-pressed',!!(PGD&&PGD.ano===+c.dataset.pgano)));
  $$('#progCorpo [data-pgh]').forEach(c=>c.setAttribute('aria-pressed',!!(PGD&&PGD.h===+c.dataset.pgh)));
  if(rolar&&PGD)box.scrollIntoView({behavior:'smooth',block:'nearest'});}
function pgDet(){
  const fechar='<button type="button" class="btn-ghost" data-pgfechar>Fechar</button>';
  if(PGD.h!=null){const [rot,a,b]=PG_FAIXAS[PGD.h],l=JG.jogos.filter(pgJogou).filter(j=>j.minutos>=a&&j.minutos<b).sort((x,y)=>y.minutos-x.minutos);
    return `<div class="pg-det"><div class="pg-rp-cab"><h3>Jogos com ${rot} <span class="tnum">${fmtN(l.length)}</span></h3><span class="pg-rp-fonte"></span>${fechar}</div>
      <div class="pg-lista">${l.map(pgLinha).join('')||'<div class="empty">Nenhum jogo aqui.</div>'}</div></div>`;}
  const ano=PGD.ano,r=RP[ano],a1=new Date().getFullYear();
  const cab=f=>`<div class="pg-rp-cab">${ano>pgA0?`<button type="button" class="btn-ghost" data-pgano="${ano-1}">‹ ${ano-1}</button>`:''}<h3>Seu ${ano}</h3>
    ${ano<a1?`<button type="button" class="btn-ghost" data-pgano="${ano+1}">${ano+1} ›</button>`:''}<span class="pg-rp-fonte">${f||''}</span>${fechar}</div>`;
  if(!r)return `<div class="pg-det">${cab()}<div class="empty">Lendo o Replay de ${ano} na Steam…</div></div>`;
  if(!r.ok){const l=JG.jogos.filter(pgJogou).filter(j=>j.ultima&&new Date(j.ultima*1000).getFullYear()===ano).sort((x,y)=>y.minutos-x.minutos);
    return `<div class="pg-det">${cab('jogos cuja última vez foi em '+ano)}<div class="pg-aviso">${esc(r.motivo||'')} Abaixo, os jogos que você jogou pela última vez em ${ano}, com as horas de sempre.</div>
      <div class="pg-lista">${l.map(pgLinha).join('')||'<div class="empty">Nenhum jogo com última vez em '+ano+'.</div>'}</div></div>`;}
  const J=r.jogos,porId={},M=PG_MES.map((_,i)=>({i,seg:0,jogos:{}}));J.forEach(g=>porId[g.appid]=g);
  r.meses.forEach(m=>{M[new Date(m.t*1000).getUTCMonth()]=Object.assign({},m,{i:new Date(m.t*1000).getUTCMonth()});});
  const mes=PGD.mes!=null&&M[PGD.mes].seg?PGD.mes:null,base=mes==null?r.seg:M[mes].seg;
  const lista=mes==null?J.map(g=>({g,seg:g.seg})):Object.entries(M[mes].jogos).map(([a,s])=>({g:porId[a],seg:s})).filter(x=>x.g&&x.seg).sort((x,y)=>y.seg-x.seg);
  const nome=g=>g.nome||'App '+g.appid,novos=J.filter(g=>g.novo&&!g.demo).length,sq=r.sequencia||{};
  const cols=M.map(m=>{const top=Object.entries(m.jogos).sort((x,y)=>y[1]-x[1]).slice(0,3).map(([a])=>porId[a]&&nome(porId[a])).filter(Boolean);
    return {rot:PG_MES[m.i],n:m.seg,txt:m.seg?fmtS(m.seg):'',tip:m.seg?top.join(', ')+' · clique para ver o mês':'nada jogado',at:`data-pgmes="${m.i}"`,on:mes===m.i};});
  const linha=({g,seg},k)=>{const pct=base?seg/base*100:0;
    return `<div class="pg-row pg-rr"${g.demo?'':` data-open="${g.appid}"`}><span class="pg-rk tnum">${k+1}</span>${art(g.appid,nome(g),pgCapa(g))}
      <div class="pg-n"><span class="pg-nome">${esc(nome(g))}${g.novo?' <em class="pg-tag">novo</em>':''}${g.demo?' <em class="pg-tag">demo</em>':''}</span>
      <span class="pg-sub">${fmtS(seg)}${mes==null?` · ${fmtN(g.sessoes)} sess${g.sessoes>1?'ões':'ão'}${g.primeira?' · jogou pela 1ª vez em '+pgMesAno(g.primeira):''}`:' em '+PG_MES[mes]}</span></div>
      <div class="pg-conq"><span class="pg-bar"><i style="width:${Math.max(1,pct)}%;background:var(--sinal)"></i></span><span class="tnum">${pct<1?'< 1':Math.round(pct)}% ${mes==null?'do ano':'do mês'}</span></div></div>`;};
  return `<div class="pg-det">${cab(`do Replay da Steam · <a href="https://store.steampowered.com/replay/${esc(r.steamid)}/${ano}" target="_blank" rel="noopener">ver na Steam ↗</a>`)}
    ${r.farm&&r.farm.n?`<div class="pg-opc">Sem <b>${fmtN(r.farm.n)} jogo${r.farm.n>1?'s':''} de farm de cartas</b> (${fmtS(r.farm.seg)}): o farm de cartas está ligado e eles não têm conquista feita.</div>`:''}
    <div class="pg-kpis pg-rk5">${pgKpi(fmtN(Math.round(r.seg/3600)),'horas jogadas')}${pgKpi(fmtN(J.length),'jogos',novos?fmtN(novos)+' novos para você':'')}
      ${pgKpi(fmtN(r.sessoes),'sessões',r.seg&&r.sessoes?'cerca de '+fmtS(r.seg/r.sessoes)+' cada':'')}${pgKpi(fmtN(r.conquistas),'conquistas',r.raras?fmtN(r.raras)+' raras':'')}
      ${pgKpi(sq.dias?fmtN(sq.dias)+' dias':'—','maior sequência',sq.inicio?'a partir de '+new Date(sq.inicio*1000).toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit'}):'')}</div>
    <h3 class="pg-h">Mês a mês <small>clique num mês</small></h3>${pgColunas(cols)}
    <h3 class="pg-h">${mes==null?'Jogo a jogo no ano':'Jogo a jogo em '+PG_MES[mes]} <small>${fmtN(lista.length)} jogo${lista.length>1?'s':''}</small></h3>
    <div class="pg-lista">${lista.map(linha).join('')||'<div class="empty">Nada jogado.</div>'}</div></div>`;}
