/* ================= conta Steam (topo) ================= */
async function carregarConta(){
  const el=$('#contaSteam');if(!el)return;
  let c;try{c=(await api('/api/config')).config;}catch(e){return;}
  const p=String(c.perfil_steam||''),local=['localhost','127.0.0.1'].includes(location.hostname),id=/^\d{17}$/.test(p);
  const dica='Você confirma na página da própria Steam. O Hunter só recebe o seu SteamID: nunca a senha, token ou cookie.';
  if(!p){el.innerHTML=local?`<a class="btn-imp" href="/kurokami/steam/entrar" title="${esc(dica)}">Entrar pela Steam</a>`:'<span class="chip-steam" title="Abra o painel no próprio PC (localhost) para entrar pela Steam">Entrar: só no PC</span>';return;}
  const pf=(RES&&RES.perfil)||{},curto=p.replace(/\/+$/,'').split('/').pop(),nome=pf.nome||(id?'Steam …'+p.slice(-4):curto.slice(0,16));
  const url=id?`https://steamcommunity.com/profiles/${p}/`:/^https:\/\/steamcommunity\.com\//.test(p)?p:`https://steamcommunity.com/id/${encodeURIComponent(curto)}/`;
  el.innerHTML=`<div class="dd"><button class="avatar" type="button" aria-haspopup="true" title="Perfil em uso: ${esc(nome)}">${pf.avatar?`<img src="${esc(pf.avatar)}" alt="" width="34" height="34">`:`<span>${esc(nome.replace(/^Steam …/,'').slice(0,1).toUpperCase())}</span>`}</button>
    <div class="ddm ddm-dir"><div class="ddm-nome">${esc(nome)}</div><a href="${esc(url)}" target="_blank" rel="noopener">Ver perfil na Steam</a>${local?`<a href="/kurokami/steam/entrar" title="${esc(dica)}">Trocar de conta</a>`:''}</div></div>`;
}
/* QR (endereço do painel para o celular, em Configurações) */
function comQR(fn){if(window.QRCode)return fn();const sc=document.createElement('script');sc.src='https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js';sc.integrity='sha384-3zSEDfvllQohrq0PHL1fOXJuC/jSOO34H46t6UQfobFOmxE5BpjjaIJY5F2/bMnU';sc.crossOrigin='anonymous';sc.onload=fn;document.head.appendChild(sc);}
document.addEventListener('keydown',e=>{if(e.key==='Escape')fecharBusca();});
/* ---- Finalizar pedido: abre o carrinho da Steam com o pedido no endereço; a extensão do Hunter põe os itens lá ---- */
/* assistente da extensão: neste PC, sem a extensão, uma faixa no topo pede permissão e conduz a instalação.
   O navegador não deixa programa nenhum instalar extensão sozinho; o usuário liga o Modo do desenvolvedor e arrasta a pasta. */
const temExt=()=>!!document.documentElement.dataset.kurokamiExt;
// a extensão entrega o que leu da sua conta na loja da Steam (seguidos, ignorados, biblioteca com DLCs) e avisa aqui
document.addEventListener('kurokami-conta',e=>{let d={};try{d=JSON.parse(e.detail)||{};}catch(x){}
  if(d.ok){toast(`Conta Steam atualizada pela extensão: ${fmtN(d.seguidos)} seguidos, ${fmtN(d.ignorados)} ignorados, ${fmtN(d.possuidos)} na biblioteca`);carregarLista().catch(()=>{});
    for(const k in FR)FR[k].velho=true;}   // Ofertas e Biblioteca recarregam com as DLCs da conta ao entrar
  else if(d.erro)toast('Extensão: '+d.erro);});
function faixaExt(forcar){
  if(temExt()||$('#aviso-ext')||!['localhost','127.0.0.1'].includes(location.hostname))return;
  let depois=false;try{depois=!!sessionStorage.getItem('kr:ext_depois');}catch(e){}
  if(!forcar&&(ls.get('ext_nao',0)||depois))return;
  const d=document.createElement('div');d.id='aviso-ext';
  d.style.cssText='background:#1f1f1f;color:#fff;padding:10px 16px;text-align:center;font-size:12.5px;line-height:1.7';
  d.innerHTML=`A <b>extensão do Hunter</b> põe os jogos no carrinho da Steam no <b>Finalizar pedido</b> e traz o que você tem na conta, <b>inclusive as DLCs</b> (a API da Steam só passa os jogos). Instalar agora? É uma vez só e leva menos de um minuto.
    <button class="btn-imp" id="extSim" type="button" style="margin-left:8px">Instalar</button> <button class="btn-ghost" id="extDepois" type="button">Agora não</button> <button class="btn-ghost" id="extNunca" type="button">Não perguntar mais</button>`;
  document.body.prepend(d);
  $('#extSim').onclick=()=>instalarExt();
  $('#extDepois').onclick=()=>{try{sessionStorage.setItem('kr:ext_depois','1');}catch(e){}d.remove();};
  $('#extNunca').onclick=()=>{ls.set('ext_nao',1);d.remove();toast('Certo. Se mudar de ideia, clique em Finalizar pedido no Carrinho.');};
}
async function instalarExt(pasta){
  const d=$('#aviso-ext');if(!d)return;
  const r=await post('/api/steam/extensao',{navegador:true,pasta:pasta===true});
  if(!r.ok){toast(r.erro||'Não consegui abrir a pasta da extensão.');return;}
  if(r.loja){   // Edge: a extensão está na loja deles, um clique em Obter
    d.innerHTML=`<div style="text-align:left;max-width:780px;margin:0 auto">Abri a página da extensão na <b>loja do Edge</b>.
      <ol style="margin:4px 0 6px 18px;padding:0"><li>Clique em <b>Obter</b> e confirme em <b>Adicionar extensão</b>.</li><li>Volte aqui e clique em <b>Pronto</b>.</li></ol>
      <button class="btn-imp" id="extPronto" type="button">Pronto</button> <button class="btn-ghost" id="extPasta" type="button">Instalar pela pasta</button> <button class="btn-ghost" id="extFechar" type="button">Fechar</button>
      <span style="font-size:11px;color:#d2d2d2;margin-left:8px">Ela só age na página do carrinho da Steam; o Hunter nunca vê senha, token ou cookie.</span></div>`;
    $('#extPronto').onclick=()=>{try{sessionStorage.setItem('kr:ext_conferir','1');}catch(e){}location.reload();};
    $('#extPasta').onclick=()=>instalarExt(true);
    $('#extFechar').onclick=()=>d.remove();
    return;}
  let copiado=false;try{await navigator.clipboard.writeText(r.pasta);copiado=true;}catch(e){}
  d.innerHTML=`<div style="text-align:left;max-width:780px;margin:0 auto">${r.aviso?`<b style="color:#ff8a94">${esc(r.aviso)}</b>`:`Abri as extensões do <b>${esc(r.navegador)}</b> (${esc(r.pagina)}) e a pasta da extensão no Explorador.`}
    <ol style="margin:4px 0 6px 18px;padding:0"><li>Na página de extensões, ligue o <b>Modo do desenvolvedor</b>.</li>
    <li><b>Arraste a pasta <code>extensao</code></b> do Explorador para a página de extensões. Ou clique em <b>Carregar sem compactação</b> e escolha a pasta${copiado?' (o caminho já está copiado: cole na barra de endereço da janela)':''}: <code style="user-select:all;word-break:break-all">${esc(r.pasta)}</code></li>
    <li>Volte aqui e clique em <b>Pronto</b>.</li></ol>
    <button class="btn-imp" id="extPronto" type="button">Pronto</button> <button class="btn-ghost" id="extFechar" type="button">Fechar</button>
    <span style="font-size:11px;color:#d2d2d2;margin-left:8px">Ela só age na página do carrinho da Steam; o Hunter nunca vê senha, token ou cookie.</span></div>`;
  $('#extPronto').onclick=()=>{try{sessionStorage.setItem('kr:ext_conferir','1');}catch(e){}location.reload();};
  $('#extFechar').onclick=()=>d.remove();
}
function conferirExt(){   // depois do "Pronto": a página recarregou; a extensão marcou o <html>?
  let conferir=false;try{conferir=!!sessionStorage.getItem('kr:ext_conferir');sessionStorage.removeItem('kr:ext_conferir');}catch(e){}
  if(conferir&&temExt()){toast('Extensão do Hunter instalada ✓ O Finalizar pedido já põe os jogos no carrinho da Steam.');return;}
  if(conferir){faixaExt(true);toast('Ainda não encontrei a extensão. Clique em Instalar para ver os passos de novo.');return;}
  faixaExt(false);
}
async function finalizar(){
  if(!CD)return;
  const nota=$('#finalNota');nota.innerHTML='';
  const nSteam=CD.itens.filter(c=>!c.possuido).length+CD.bundles.length;
  if(!nSteam){toast('O carrinho está vazio.');return;}
  if(!temExt()){faixaExt(true);window.scrollTo(0,0);toast('Instale a extensão do Hunter (faixa no topo) e clique em Finalizar pedido de novo.');return;}
  const w=window.open('about:blank','_blank');if(w)w.opener=null;   // abre já, no clique (o navegador não bloqueia); a Steam não alcança o painel
  const b=$('#btnFinalizar');b.disabled=true;let r;try{r=await post('/api/steam/carrinho');}finally{b.disabled=false;}
  if(!r.ok){if(w)w.close();toast('Erro: '+(r.erro||'?'));}
  else{
    if(w)w.location=r.url;else nota.insertAdjacentHTML('afterbegin',`<a class="btn-ghost" href="${esc(r.url)}" target="_blank" rel="noopener" style="display:inline-block;text-decoration:none;margin-top:6px">Abrir o carrinho da Steam</a>`);
    toast(`${r.n} item(ns) a caminho do carrinho da Steam: a extensão do Hunter adiciona na aba que abriu. Conclua o pagamento lá.`);
  }
  if((r.sem_pacote||[]).length)nota.insertAdjacentHTML('beforeend',`<div class="hint" style="color:#ff8a94;font-size:11.5px">Sem pacote conhecido (abra a página): ${r.sem_pacote.map(esc).join(', ')}</div>`);
}
