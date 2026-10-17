/* Metas para jogar mais (Status > Progresso; radar/metas.py): jogar X h por dia e platinar N jogos por semana/mês/ano.
   O pop-up de "meta batida" aparece em qualquer aba (o aviso do Windows sai do Hunter na hora; este espera o painel abrir). */
let MT=null;
const mtH=m=>{const h=m/60;return (h<10?h.toFixed(1):String(Math.round(h))).replace('.',',')+' h';};
const MT_POR={semana:'por semana',mes:'por mês',ano:'por ano'};
async function renderMetas(){
  const box=$('#metasBox');if(!box)return;
  try{MT=await api('/api/metas');}catch(e){return;}
  if(box.contains(document.activeElement)&&/INPUT|SELECT/.test(document.activeElement.tagName))return;   // não apaga o que está sendo digitado
  desenharMetas();}
function desenharMetas(){
  const box=$('#metasBox'),m=MT.meta,alvo=m.horas_dia*60;if(!box||!MT)return;
  const mx=Math.max(alvo,...MT.dias.map(d=>d.min),1);
  const dia=MT.dias.map(d=>{const dt=new Date(d.dia+'T12:00:00'),ok=alvo>0&&d.min>=alvo;
    return [`<i class="${ok?'ok':''}" style="height:${Math.max(d.min?6:2,Math.round(d.min/mx*100))}%" title="${dt.toLocaleDateString('pt-BR',{day:'2-digit',month:'short'}).replace('.','')}: ${d.min?mtH(d.min):'não jogou'}"></i>`,`<em>${dt.getDate()}</em>`];});
  const jogosHoje=MT.hoje_jogos.length?`<div class="mt-lista">Hoje: ${MT.hoje_jogos.map(x=>`<a href="#" data-open="${x.appid}">${esc(x.nome)}</a> ${mtH(x.min)}`).join(' · ')}</div>`:'<div class="mt-lista">Nenhum jogo registrado hoje ainda.</div>';
  const hoje=alvo?`<div class="mt-st"><b class="tnum">${mtH(MT.hoje)}</b> de ${mtH(alvo)} hoje${MT.hoje>=alvo?' · <span class="mt-ok">meta batida</span>':''}${MT.sequencia>1?` · ${MT.sequencia} dias seguidos batendo a meta`:''}</div>
      <div class="fx-barra"><i style="width:${Math.min(100,MT.hoje/alvo*100)}%"></i></div>${jogosHoje}<div class="mt-dias" aria-label="Horas jogadas nos últimos 14 dias" title="Últimos 14 dias; a linha é a meta"><div class="mt-barras">${dia.map(x=>x[0]).join('')}<b class="mt-meta" style="bottom:${Math.min(100,alvo/mx*100)}%"></b></div><div class="mt-rot">${dia.map(x=>x[1]).join('')}</div></div>`
    :'<div class="mt-st mt-off">Desligada: ponha as horas por dia que você quer jogar.</div>';
  const fim=m.terminar_qtd?`<div class="mt-st"><b class="tnum">${MT.terminados.length}</b> de ${m.terminar_qtd} ${m.terminar_qtd>1?'jogos platinados':'jogo platinado'} ${MT_POR[m.terminar_por]}${MT.terminados.length>=m.terminar_qtd?' · <span class="mt-ok">meta batida</span>':''}</div>
      <div class="fx-barra"><i style="width:${Math.min(100,MT.terminados.length/m.terminar_qtd*100)}%"></i></div>
      ${MT.terminados.length?`<div class="mt-lista">${MT.terminados.slice(0,6).map(x=>`<a href="#" data-open="${x.appid}">${esc(x.nome)}</a>`).join(' · ')}</div>`:'<div class="mt-lista">Nenhum ainda neste período (conta o que for platinado depois desta versão).</div>'}`
    :'<div class="mt-st mt-off">Desligada: ponha quantos jogos você quer platinar.</div>';
  const agora=MT.agora?`<div class="mt-agora"><i></i>Jogando agora: <a href="#" data-open="${MT.agora.appid}">${esc(MT.agora.nome)}</a> <span>· as horas de hoje contam ao vivo</span></div>`:'';
  box.innerHTML=`<div class="mt"><h3>Metas para jogar mais</h3>${agora}
    <div class="mt-col"><label>Jogar <input type="number" id="mtHoras" min="0" max="24" step="0.25" value="${m.horas_dia||''}" placeholder="0"> h por dia</label>${hoje}</div>
    <div class="mt-col"><label>Platinar <input type="number" id="mtQtd" min="0" max="99" step="1" value="${m.terminar_qtd||''}" placeholder="0"> jogos <select id="mtPor">${Object.entries(MT_POR).map(([k,t])=>`<option value="${k}"${m.terminar_por===k?' selected':''}>${t}</option>`).join('')}</select></label>${fim}</div>
    <p class="mt-nota">0 desliga a meta. Com o Hunter aberto, o jogo que está rodando conta ao vivo (a cada 30 s); a Steam confirma o tempo quando o jogo fecha, sem contar em dobro. As horas contam a partir de quando o Hunter passou a acompanhar${MT.base?'':' (a primeira leitura ainda vai ser feita)'}${MT.farm?'; jogos de farm de cartas não contam':''}. O aviso sai no Windows e aqui.</p></div>`;}
async function salvarMetas(){
  const n={horas_dia:+$('#mtHoras').value||0,terminar_qtd:+$('#mtQtd').value||0,terminar_por:$('#mtPor').value};
  const r=await post('/api/config',{config:{metas:n}});if(r.ok===false)return;
  toast('Metas salvas');renderMetas();}
document.addEventListener('change',e=>{if(e.target.closest&&e.target.closest('#metasBox')&&/^mt(Horas|Qtd|Por)$/.test(e.target.id))salvarMetas();});
/* pop-up como o de conquista da Steam: um por vez, some sozinho em 8 s; depois o painel avisa o Hunter que já mostrou */
let MTPOP=false;
async function metasPoll(){
  if(MTPOP||document.hidden)return;
  let r;try{const x=await fetch('/api/metas');if(!x.ok)return;r=await x.json();}catch(e){return;}
  const p=r.pendentes||[];if(!p.length)return;
  MTPOP=true;
  for(const a of p){await new Promise(fim=>{const el=document.createElement('div');el.className='mt-pop';el.setAttribute('role','status');
    el.innerHTML=`<i class="ic">★</i><div><small>Meta batida</small><b>${esc(a.titulo)}</b><span>${esc(a.texto)}</span></div>`;
    document.body.appendChild(el);requestAnimationFrame(()=>el.classList.add('v'));
    const sai=()=>{el.classList.remove('v');setTimeout(()=>{el.remove();fim();},400);};el.onclick=sai;setTimeout(sai,8000);});}
  try{await fetch('/api/metas_visto',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({n:p.length})});}catch(e){}
  MTPOP=false;if(S.tab==='prog')renderMetas();}
setTimeout(metasPoll,4000);setInterval(metasPoll,30000);
setInterval(()=>{if(S.tab==='prog'&&!document.hidden&&MT&&(MT.agora||MT.meta.horas_dia))renderMetas();},30000);   // ao vivo: o cartão se atualiza enquanto há jogo rodando
