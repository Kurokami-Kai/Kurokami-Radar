/* ================= carrinho ================= */
let CD=null;
const MODOS=[['conta','Para a minha conta'],['presente','Presente'],['privado','Privado']];
function modoSel(t,id,m){return `<select class="mini modosel" data-cmodo="${t}${id}" title="Como entra no carrinho da Steam">${MODOS.map(([v,n])=>`<option value="${v}"${v===(m||'conta')?' selected':''}>${n}</option>`).join('')}</select>`;}
async function renderCarr(){
  CD=await api('/api/carrinho');CARR=CD.itens.map(i=>({appid:i.appid,modo:i.modo,loja:i.pedida})).concat(CD.bundles.map(b=>({bundle:b.bundle,modo:b.modo})));$('#carrN').textContent=CARR.length?'('+CARR.length+')':'';
  const it=CD.itens;
  $('#carrNote').textContent=(it.length||CD.bundles.length)?`${it.length} item(ns)${CD.bundles.length?` + ${CD.bundles.length} bundle(s)`:''}`:'';
  const ofC=c=>c.lojas.find(l=>l.loja===c.loja)||{};
  const linha=c=>{const sel=ofC(c);
    return `<div class="crow">${art(c.appid,c.nome,c.capa,{small:true})}
      <div><div class="nm" data-open="${c.appid}">${esc(c.nome)}</div><div class="flags" style="margin-top:4px">${c.sumiu?'<span class="flag">Não está à venda na Steam agora</span>':''}${c.possuido?'<span class="flag own">Você já tem</span>':''}${c.em_bundle.length?`<span class="flag">também no bundle ${esc(c.em_bundle[0])}</span>`:''}${fimTxt(c.fim)?`<span class="flag">⏳ ${fimTxt(c.fim)}</span>`:''}${c.tipo_oferta==='selo'?seloBadge(c):recPill(c)}${c.piso!=null?`<span class="motivo" style="margin:0">menor de sempre ${brl(c.piso)}</span>`:''}</div></div>
      <div class="cesc"><span class="lojatag" title="Loja">Steam</span>${modoSel('a',c.appid,c.modo)}</div>
      ${priceBlock({preco:sel.preco,cheio:sel.cheio,corte:sel.corte||0})}
      <button class="xbtn" data-cart="${c.appid}" title="Tirar do carrinho">×</button></div>`;};
  const linhaB=b=>`<div class="crow">${art(b.bundle,b.nome,b.capa,{small:true})}
      <div><div class="nm"><a href="https://store.steampowered.com/bundle/${b.bundle}/" target="_blank" rel="noopener" style="color:#fff">📦 ${esc(b.nome)}</a></div>
        <div class="motivo">${b.itens.length} itens${b.itens.some(i=>i.tenho)?` · você já tem ${b.itens.filter(i=>i.tenho).length} (descontado)`:''}${b.itens.some(i=>i.no_carrinho)?` · <span style="color:#ff8a94">${b.itens.filter(i=>i.no_carrinho).length} também avulso no carrinho</span>`:''}</div>
        <div class="motivo" title="${esc(b.itens.map(i=>i.nome).join(', '))}">${esc(b.itens.slice(0,4).map(i=>i.nome).join(', '))}${b.itens.length>4?'…':''}</div></div>
      <div class="cesc"><span class="lojatag">Steam</span>${modoSel('b',b.bundle,b.modo)}</div>${priceBlock({preco:b.preco,cheio:b.cheio||b.preco,corte:b.cheio&&b.preco<b.cheio?Math.round(100*(1-b.preco/b.cheio)):0})}
      <button class="xbtn" data-cartb="${b.bundle}" title="Tirar do carrinho">×</button></div>`;
  const grupos={};it.forEach(c=>(grupos[c.loja]=grupos[c.loja]||[]).push(c));if(CD.bundles.length)grupos.Steam=grupos.Steam||[];
  const lojas=Object.keys(grupos).sort((a,b)=>(b==='Steam')-(a==='Steam')||a.localeCompare(b,'pt-BR'));
  const subt=l=>grupos[l].reduce((s,c)=>s+(c.possuido?0:ofC(c).preco||0),0)+(l==='Steam'?CD.bundles.reduce((s,b)=>s+(b.preco||0),0):0);
  $('#carrLista').innerHTML=lojas.length?lojas.map(l=>{const n=grupos[l].length+(l==='Steam'?CD.bundles.length:0);
    return `<div class="cgrp"><h3>${esc(l)}</h3><span class="sub">${n} ${n>1?'itens':'item'} · ${brl(subt(l))}</span><span class="aside">vai para o carrinho da Steam pela extensão</span></div>`
      +grupos[l].map(linha).join('')+(l==='Steam'?CD.bundles.map(linhaB).join(''):'');}).join(''):
    '<div class="empty">Carrinho vazio (só da Steam: jogo de outra loja abre a página dela). Use o + nas listas, o botão na ficha do jogo, a busca ao lado ou "Trazer o carrinho da Steam".</div>';
  let total=0,cheio=0,pisoTot=0,semPreco=0;
  CD.bundles.forEach(b=>{if(b.preco==null){semPreco++;return;}total+=b.preco;cheio+=b.cheio||b.preco;pisoTot+=b.preco;});
  it.forEach(c=>{const sel=ofC(c);if(sel.preco==null){semPreco++;return;}
    total+=sel.preco;cheio+=sel.cheio||sel.preco;pisoTot+=Math.min(sel.preco,c.piso??sel.preco);});
  $('#carrResumo').innerHTML=`<div class="tot big"><span>Valor total estimado</span><b>${(it.length||CD.bundles.length)?brl(total):'R$ 0,00'}</b></div>
    <button class="btn-finalizar" id="btnFinalizar" type="button">Finalizar pedido</button><div id="finalNota"></div><a href="#lista" style="display:block;text-align:center;color:var(--blue);font-size:12px;margin:2px 0 8px">Continuar comprando</a>
    ${lojas.length>1?lojas.map(l=>`<div class="tot"><span>${esc(l)}</span><b>${brl(subt(l))}</b></div>`).join(''):''}
    <div class="tot"><span>Preço cheio</span><b>${brl(cheio)}</b></div>
    <div class="tot"><span>Você economiza</span><b style="color:var(--disc-fg)">${brl(cheio-total)}${cheio?` (${Math.round(100*(1-total/cheio))}%)`:''}</b></div>
    <div class="tot"><span>Se cada um estivesse no menor de sempre</span><b>${brl(pisoTot)}</b></div>
    <div class="tot"><span>Diferença para os pisos</span><b>${brl(total-pisoTot)}</b></div>
    ${semPreco?`<div class="hint" style="color:var(--dim);font-size:11px">${semPreco} jogo(s) sem preço ainda (chega na próxima checagem).</div>`:''}
    ${CD.sugestoes.some(x=>x.diferenca<0)?`<div class="hint" style="color:var(--disc-fg);font-size:11.5px;margin-top:6px">Há bundle mais barato para parte do carrinho ↓</div>`:''}`;
  $('#btnFinalizar').onclick=finalizar;
  const orc=ls.get('orc',0);$('#orc').value=orc||'';
  $('#orcBar').innerHTML=orc?`<div class="tot"><span>${total>orc*100?'Passou':'Sobra'}</span><b>${brl(Math.abs(orc*100-total))}</b></div><div class="bar${total>orc*100?' over':''}"><i style="width:${Math.min(100,total/(orc*100)*100)}%"></i></div>`:'<div class="hint" style="color:var(--dim);font-size:11px">Defina um valor para ver quanto sobra.</div>';
  $('#carrBundles').innerHTML=CD.sugestoes.length?`<div class="shead"><h2>Bundles com itens do seu carrinho</h2><span class="aside">preço já descontando o que você tem</span></div>
    <div class="rows">${CD.sugestoes.map(b=>`<div class="srow" style="grid-template-columns:minmax(0,1fr) auto auto">
      <span class="tt"><div><a href="https://store.steampowered.com/bundle/${b.bundle}/" target="_blank" rel="noopener" style="color:inherit">📦 ${esc(b.nome)}</a></div>
      <div class="motivo">cobre ${b.comuns.length} do carrinho: ${esc(b.comuns.join(', '))}${b.extras.length?` · traz também ${b.extras.length}: ${esc(b.extras.slice(0,3).join(', '))}${b.extras.length>3?'…':''} (${brl0(b.extras_valor)} cheio)`:''}</div>
      <div class="motivo">${b.diferenca<0?`<b style="color:var(--disc-fg)">economiza ${brl(-b.diferenca)}</b>`:`custa ${brl(b.diferenca)} a mais`} que os ${b.comuns.length} separados (${brl(b.separado)})</div></span>
      ${priceBlock({preco:b.preco,cheio:b.separado,corte:b.diferenca<0?Math.round(100*(1-b.preco/b.separado)):0})}
      <span style="display:flex;flex-direction:column;gap:4px"><button class="btn-imp" data-trocar="${b.bundle}|${b.comuns_ids.join(',')}" style="font-size:11.5px;padding:5px 8px">Trocar pelos itens</button><button class="btn-ghost" data-cartb="${b.bundle}" style="font-size:11.5px">Só adicionar</button></span></div>`).join('')}</div>`:'';
  $('#carrSteam').style.display=(CD.steam||[]).length?'':'none';$('#carrSteam').textContent=`Trazer o carrinho da Steam (${(CD.steam||[]).length})`;
}
$('#carrBundles').addEventListener('click',async e=>{const t=e.target.closest('[data-trocar]');if(!t)return;const [bid,ids]=t.dataset.trocar.split('|');const rem=new Set(ids.split(',').map(Number));
  CARR=CARR.filter(c=>!(c.appid&&rem.has(c.appid)));if(!CARR.some(c=>c.bundle===+bid))CARR.push({bundle:+bid,modo:'conta'});await salvarCarr();toast('Trocado pelo bundle');renderCarr();});
$('#carrLista').addEventListener('change',async e=>{
  const s=e.target.closest('[data-cmodo]');if(!s)return;const t=s.dataset.cmodo[0],id=+s.dataset.cmodo.slice(1);
  const c=CARR.find(x=>t==='b'?x.bundle===id:x.appid===id);if(c)c.modo=s.value;await salvarCarr();renderCarr();});
$('#orc').addEventListener('change',e=>{ls.set('orc',+e.target.value||0);renderCarr();});
$('#carrLimpa').addEventListener('click',async()=>{CARR=[];await salvarCarr();renderCarr();});
$('#carrSteam').addEventListener('click',async()=>{const ids=(CD&&CD.steam)||[];let n=0;ids.forEach(id=>{if(!CARR.some(c=>c.appid===id)){CARR.push({appid:id,modo:'conta',loja:'Steam'});n++;}});
  await salvarCarr();renderCarr();toast(n?`${n} jogo(s) do carrinho da Steam`:'Já estavam todos aqui');});
let BUSCA={n:0,t:null};
function fecharBusca(){$('#buscaRes').hidden=true;}
async function buscar(){const q=$('#busca').value.trim(),box=$('#buscaRes');if(!q){fecharBusca();return;}
  const n=++BUSCA.n;box.hidden=false;box.innerHTML='<div class="empty" style="padding:14px">buscando…</div>';
  let d;try{d=await api('/api/buscar?q='+encodeURIComponent(q));}catch(e){if(n===BUSCA.n)box.innerHTML=`<div class="empty">Erro: ${esc(e.message)}</div>`;return;}
  if(n!==BUSCA.n)return;   // chegou uma busca mais nova
  const no=id=>CARR.some(c=>c.appid===id);
  box.innerHTML=`<div class="rhead"><span>${d.itens.length?d.itens.length+' resultado(s) · clique para adicionar':'Nada encontrado.'}</span><button type="button" data-fechar title="Fechar (Esc)">×</button></div>`+(d.itens.length?`<div class="res">${d.itens.map(i=>{const ja=no(i.appid);
    return `<button type="button" class="ritem${ja?' feito':''}" data-addcarr="${i.appid}" data-mon="${i.na_lista?0:1}" title="${ja?'Já está no carrinho':'Adicionar ao carrinho: '+esc(i.nome)}"${ja?' disabled':''}>${art(i.appid,i.nome,i.capa,{small:true})}
    <span class="rb"><span class="rn">${esc(i.nome)}</span><span class="motivo">${i.possuido?'você já tem · ':''}${i.preco!=null?brl(i.preco)+(i.corte?' (-'+i.corte+'%)':''):''}</span></span><span class="rok">${ja?'✓':'+'}</span></button>`;}).join('')}</div>`:'');}
$('#buscaBtn').addEventListener('click',buscar);
$('#busca').addEventListener('keydown',e=>{if(e.key==='Enter'){clearTimeout(BUSCA.t);buscar();}else if(e.key==='Escape'){fecharBusca();}});
$('#busca').addEventListener('input',()=>{clearTimeout(BUSCA.t);const q=$('#busca').value.trim();if(q.length<2){BUSCA.n++;fecharBusca();return;}BUSCA.t=setTimeout(buscar,450);});
$('#busca').addEventListener('focus',()=>{if($('#buscaRes').innerHTML&&$('#busca').value.trim())$('#buscaRes').hidden=false;});
document.addEventListener('click',e=>{if(!$('#buscaRes').hidden&&!e.target.closest('#cbusca'))fecharBusca();});
$('#buscaRes').addEventListener('click',async e=>{if(e.target.closest('[data-fechar]')){fecharBusca();return;}
  const a=e.target.closest('[data-addcarr]');if(!a||a.disabled)return;
  a.disabled=true;a.classList.add('feito');a.querySelector('.rok').textContent='✓';
  const id=+a.dataset.addcarr;if(a.dataset.mon==='1'){await post('/api/extra',{appid:id});await carregarLista();}
  if(!CARR.some(c=>c.appid===id)){CARR.push({appid:id,modo:'conta'});await salvarCarr();}
  toast('No carrinho da Steam');renderCarr();});
