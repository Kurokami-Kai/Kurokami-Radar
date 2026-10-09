/* ================= status / ações ================= */
const VERSAO_PAGINA='0.17.2';
function nVitrine(){return VIT?['selo','novo','igual','24m'].reduce((s,t)=>s+((VIT[t]||{}).total||0),0):null;}
function atualizarStatus(){const el=$('#stTopo');if(el&&VIT)el.innerHTML=`<b>${nVitrine()}</b> na vitrine · ${fmtN(RES.na_lista)} na lista`;}
async function carregarResumo(){
  RES=await api('/api/resumo');$('#ver').textContent=RES.versao;
  if(RES.userdata_dias!=null&&RES.userdata_dias>30&&!$('#aviso-ud')){const d=document.createElement('div');d.id='aviso-ud';
    d.style.cssText='background:#a3222e;color:#fff;padding:8px 16px;text-align:center;font-size:12.5px';
    d.innerHTML=`Seu <b>userdata.json</b> tem ${RES.userdata_dias} dias: DLCs compradas depois disso não aparecem como suas. Abra a loja da Steam logado (com a extensão do Hunter 1.1 ou mais nova ele se atualiza sozinho) ou use "Já tenho" no jogo.`;
    document.body.prepend(d);}
  const at=RES.atualizacao;if(at&&at.tem_nova&&!$('#aviso-att')){const d=document.createElement('div');d.id='aviso-att';
    d.style.cssText='background:#6e0a14;color:#fff;padding:8px 16px;text-align:center;font-size:13px';
    d.innerHTML=`Versão nova do Kurokami Hunter: <b>${esc(at.nova)}</b> (você tem a ${esc(at.atual)}). <button id="btnAtt" style="margin-left:10px;background:#d63031;color:#fff;border:0;padding:4px 10px;cursor:pointer;font-weight:bold">Atualizar agora</button> <a href="${esc(at.pagina)}" target="_blank" rel="noopener" style="color:#ffd6d9;margin-left:8px">novidades</a>`;
    document.body.prepend(d);$('#btnAtt').onclick=async()=>{await post('/api/atualizar_app');toast('Abrindo a janela de atualização…');};}
  const bf=RES.biblioteca_falhou;if($('#aviso-bib')&&!bf)$('#aviso-bib').remove();
  if(bf&&!$('#aviso-bib')){const d=document.createElement('div');d.id='aviso-bib';
    d.style.cssText='background:#a8611c;color:#fff;padding:8px 16px;text-align:center;font-size:12.5px';
    const recusada=/\b(401|403)\b/.test(bf.erro||'');
    d.innerHTML=`A biblioteca não atualizou em ${fmtISO(bf.quando)}: a API da Steam falhou (${esc(bf.erro||'')}).${bf.mantida?' Mantive a biblioteca anterior.':''}${recusada?' A chave da Web API foi recusada: gere outra em steamcommunity.com/dev/apikey e cole em <b>Chaves e perfil…</b> (botão direito no ícone do Hunter, perto do relógio).':''}`;
    document.body.prepend(d);}
  if(RES.versao!==VERSAO_PAGINA&&!$('#aviso-versao')){const d=document.createElement('div');d.id='aviso-versao';
    d.style.cssText='background:#d63031;color:#fff;padding:10px 16px;text-align:center;font-size:13px';
    d.innerHTML=`O Hunter que está rodando é a versão <b>${esc(RES.versao)}</b>, mas os arquivos são da <b>${VERSAO_PAGINA}</b>. Clique com o direito no ícone da bandeja → <b>Sair</b> e abra de novo (ou "Reiniciar", nas versões novas).`;
    document.body.prepend(d);}
  const P=RES.progresso||{};const pct=P.total?Math.round(100*P.atual/P.total):null;
  let t=`<span id="stTopo"><b>${nVitrine()??'…'}</b> na vitrine · ${fmtN(RES.na_lista)} na lista</span>`;
  if(P.ativo)t+=`<br><span style="color:var(--sinal)">verificação ${P.modo==='completa'?'completa':'rápida'}: ${esc((P.etapa||'').slice(0,42))}${pct!=null?' '+pct+'%':''}</span> ▾`;
  else if(RES.na_bandeja)t+=`<br>${RES.estado==='erro'?'<span class="err">erro na última checagem</span> · ':''}próxima: ${fmtISO(RES.proxima)} ▾`;
  else t+='<br>checado '+fmtISO(RES.atualizado);
  $('#status').innerHTML=t;
  $('#progTopo').style.width=P.ativo?(pct!=null?Math.max(3,pct):35)+'%':'0';
  if(!$('#progBox').hidden)renderProg();$('#btnPausa').textContent=RES.pausado?'Retomar alertas':'Pausar alertas';
  $('#btnVerif').style.display=RES.na_bandeja?'':'none';
  const av=(RES.perfil||{}).avatar;if(av&&av!==carregarResumo.av){carregarResumo.av=av;carregarConta();}  // o avatar chega depois da 1ª consulta
}
function renderProg(){const P=RES.progresso||{};const u=P.ultima;const min=s=>s>=90?Math.round(s/60)+' min':s+' s';
  $('#progBox').innerHTML=P.ativo?`<h5>Verificação ${P.modo==='completa'?'completa':'rápida'} em andamento · ${min(P.decorrido||0)}</h5>
      <div>${esc(P.etapa||'')}${P.total?` — ${fmtN(P.atual)} de ${fmtN(P.total)}`:''}</div>
      ${P.total?`<div class="bar"><i style="width:${100*P.atual/P.total}%"></i></div>`:''}<pre>${esc((P.log||[]).join('\n'))}</pre>`:
    `<h5>Nenhuma verificação rodando agora</h5>
     ${u?`<div>Última: ${u.modo==='completa'?'completa':'rápida'}, ${u.ok?'ok':'<span style="color:#ef6f6a">com erro</span>'} em ${min(u.duracao)} · ${esc(u.resumo||'')}</div>`:''}
     <div style="margin-top:6px;color:#979797">Próxima rápida: ${fmtISO(RES.proxima)||'—'} · Última completa: ${fmtISO(RES.ult_completa)||'nunca'}${RES.completa_dias?` · completa a cada ${RES.completa_dias} dias`:''}</div>
     <div style="margin-top:6px;color:#979797">Rápida: preços nas lojas (a cada 30 min). Completa: também catálogo, biblioteca, DLCs, edições e histórico, sem limite de ritmo.</div>
     ${(P.log||[]).length?`<pre>${esc(P.log.join('\n'))}</pre>`:''}`;}
$('#status').addEventListener('click',()=>{$('#progBox').hidden=!$('#progBox').hidden;if(!$('#progBox').hidden)renderProg();});
document.addEventListener('click',e=>{if(!e.target.closest('#progBox')&&!e.target.closest('#status'))$('#progBox').hidden=true;});
$('#btnPausa').addEventListener('click',async()=>{const r=await post('/api/pausar');toast(r.pausado?'Notificações pausadas':'Notificações retomadas');carregarResumo();});
$('#btnVerif').addEventListener('click',async()=>{const r=await post('/api/verificar');if(!r.ok){toast(r.erro);return;}toast('Checando…');
  pollResumo.ativo=true;setTimeout(()=>carregarResumo().catch(()=>{}),1500);});
async function carregarLista(){const d=await api('/api/lista');L=d.itens;IDX=new Map(L.map(o=>[o.appid,o]));render();}
function render(){if(FR[S.tab])mostraFrame(S.tab);else if(S.tab==='lista')renderLista();else if(S.tab==='carr')renderCarr();else if(S.tab==='notif')renderNotif();else renderCfg();}

async function pollResumo(){try{await carregarResumo();}catch(e){}const P=(RES&&RES.progresso)||{};
  if(pollResumo.ativo&&!P.ativo){pollResumo.ativo=false;Object.keys(FR).forEach(k=>{FR[k].velho=true;});await carregarLista();try{VIT=await api('/api/vitrine');atualizarStatus();}catch(e){}toast('Verificação concluída');}
  if(P.ativo)pollResumo.ativo=true;setTimeout(pollResumo,P.ativo?3000:30000);}
(async()=>{try{const c=await api('/api/carrinho');CARR=c.itens.map(i=>({appid:i.appid,modo:i.modo,loja:i.pedida})).concat(c.bundles.map(b=>({bundle:b.bundle,modo:b.modo})));$('#carrN').textContent=CARR.length?'('+CARR.length+')':'';}catch(e){}
  const h=location.hash.slice(1);  // #vale, #lista... (o resumo "Tipo ligado" abre a vitrine com #vale)
  setTab(['vale','lista','bib','carr','notif','cfg'].includes(h)?h:['vale','lista','bib','carr','notif','cfg'].includes(S.tab)?S.tab:'vale');await carregarResumo();await carregarLista();
  if(!VIT){try{VIT=await api('/api/vitrine');atualizarStatus();}catch(e){}}setTimeout(pollResumo,3000);
  carregarConta();setTimeout(conferirExt,600);   // a extensão marca o <html> no fim do carregamento
  if(location.search.includes('steam=ok')){history.replaceState(null,'',location.pathname+location.hash);setTab('cfg');toast('Entrou pela Steam: perfil atualizado. A lista e a biblioteca passam para este perfil na próxima verificação (use "Verificar agora").');}})();

/* calor do desconto: até -49% frio, -50% morno, -75% quente, -90% brasa (ver docs/decisoes.md, "Produto") */
const calorDe=n=>n>=90?3:n>=75?2:n>=50?1:0;
function aquecer(){document.querySelectorAll('.pct,.pc').forEach(e=>{const m=/(\d+)\s*%/.exec(e.textContent),q=m?String(calorDe(+m[1])):null;if(!q)delete e.dataset.calor;else if(e.dataset.calor!==q)e.dataset.calor=q;});}
let aqPend=0;new MutationObserver(()=>{if(!aqPend)aqPend=requestAnimationFrame(()=>{aqPend=0;aquecer();});}).observe(document.body,{childList:true,subtree:true});aquecer();
