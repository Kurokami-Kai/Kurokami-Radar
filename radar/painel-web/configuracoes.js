/* ================= configurações ================= */
let CFG=null,TGTOK=false;
const CFG_SECOES=[['avisos','Avisos','o que dispara um aviso'],['lojas','Lojas','de onde pode vir'],['notif','Notificações','no Windows, silêncio'],['telegram','Telegram','avisos no celular'],
  ['freq','Frequência','de quanto em quanto tempo'],['steam','Steam inteira','todas as promoções'],['keyshops','Keyshops','GG.deals'],
  ['dlc','DLCs','no custo completo'],['acesso','Celular e outros PCs','abrir pela rede']];
async function renderCfg(){
  const d=await api('/api/config');CFG=d.config;TGTOK=!!d.telegram_token;const c=CFG;
  const lojas=[...new Set([...(d.lojas_itad||[]),...c.lojas])].sort((a,b)=>a.localeCompare(b));
  const marc=new Set(c.lojas.map(x=>x.toLowerCase()));
  // peças: linha (título, explicação, controle), interruptor e número com unidade
  const row=(t,h,ctl)=>`<div class="cfg-row"><div class="cfg-t"><b>${t}</b>${h?`<span>${h}</span>`:''}</div><div class="cfg-c">${ctl}</div></div>`;
  const sw=(p,v,t)=>`<label class="cfg-sw"><input type="checkbox" data-k="${p}" ${v?'checked':''} aria-label="${esc(t)}"><i></i></label>`;
  const num=(p,v,step,min,max,un,pre)=>`<span class="cfg-num${pre?' pre':''}"><input type="number" data-k="${p}" value="${v}" step="${step||1}" min="${min??0}"${max!=null?` max="${max}"`:''}>${un?`<em>${un}</em>`:''}</span>`;
  const swRow=(p,v,t,h)=>row(t,h,sw(p,v,t));
  // Telegram: bot gratuito; o token vai para o Gerenciador de Credenciais (nunca para o config.json) e a página só mostra o estado
  const tgGuia=aberto=>`<details class="tg-guia"${aberto?' open':''}><summary>Como configurar (cada pessoa cria o seu bot, leva 2 minutos)</summary><ol>
      <li>No Telegram, procure <b>@BotFather</b> (o oficial, com o selo azul) e envie <b>/newbot</b>.</li>
      <li>Ele pede um <b>nome</b> (aparece na conversa, pode ser "Kurokami Hunter") e um <b>usuário</b> que termine em <b>bot</b>, como <b>meu_kurokami_bot</b>. Se o usuário já existir, tente outro.</li>
      <li>O BotFather responde com um <b>token</b>, parecido com <b>123456:ABC…</b>. Copie e cole em "Token do bot" abaixo; clique em <b>Conectar</b>.</li>
      <li>Abra o seu bot no Telegram (o link <b>t.me/…</b> que o BotFather mandou), toque em <b>Iniciar</b> e volte aqui; clique em <b>Vincular conversa</b>.</li>
      <li>Ligue "Avisar também no Telegram" e clique em <b>Enviar teste</b>. Pronto: os avisos chegam no celular.</li></ol>
      <p>O token é como uma senha: fica só neste PC e não deve ser mandado a ninguém. Se vazar, envie <b>/revoke</b> ao BotFather e conecte de novo. Só quem mandar mensagem ao bot antes do passo 4 é vinculado, então não compartilhe o link do bot até terminar.</p></details>`;
  const tgHtml=()=>{const t=(CFG.notificacoes||{}).telegram||{};
    if(!TGTOK)return `${tgGuia(true)}
      ${row('Token do bot','Fica só neste PC, no Gerenciador de Credenciais do Windows.',`<input class="cfg-txt" id="tgTok" type="password" autocomplete="off" placeholder="123456:ABC…"><button class="btn-go2" data-tg="token" type="button">Conectar</button>`)}`;
    if(!t.chat_id)return `${tgGuia(true)}<div class="hint">Bot conectado. Agora abra o bot no Telegram, toque em <b>Iniciar</b> (ou mande qualquer mensagem) e clique em Vincular.</div>
      ${row('Sua conversa','',`<button class="btn-go2" data-tg="vincular" type="button">Vincular conversa</button><button class="btn-ghost" data-tg="remover" type="button">Trocar o bot</button>`)}`;
    return `${tgGuia(false)}${swRow('notificacoes.telegram.ativo',t.ativo,'Avisar também no Telegram','Mesmos avisos, mesmo horário de silêncio. Os botões só levam a links da internet (o painel do seu PC não abre no celular).')}
      ${row('Conexão','Bot conectado e conversa vinculada.',`<button class="btn-ghost" data-tg="testar" type="button">Enviar teste</button><button class="btn-ghost" data-tg="remover" type="button">Desconectar</button>`)}`;};
  const sec=(id,t,p,corpo)=>`<section class="cfg-sec" data-sec="${id}" hidden><header><h3>${t}</h3>${p?`<p>${p}</p>`:''}</header>${corpo}</section>`;
  const a=c.alerta,k=c.keyshops,dl=c.dlc,n=c.notificacoes||{},si=(n.silencio||{}),iv=c.intervalos_minutos,tp=a.tipos||{selo:true};
  const FREQ={selo:'~0,2 avisos por semana (0,7 em grandes promoções)',novo:'~2 avisos por semana (6 em grandes promoções)',
    igual:'~14 avisos por semana (34 em grandes promoções)','24m':'~2 avisos por semana (3 em grandes promoções)'};
  const atual=ls.get('cfgSec','avisos');
  $('#cfgForm').innerHTML=`<div class="cfgx">
   <nav class="cfg-nav" role="tablist" aria-label="Seções das configurações">${CFG_SECOES.map(([id,t,sub])=>
     `<button type="button" role="tab" data-sec="${id}" aria-selected="${id===atual}">${t}<small>${sub}</small></button>`).join('')}</nav>
   <div class="cfg-main">
   ${sec('avisos','Avisos','Que tipo de preço vira notificação. Ligar um tipo não dispara avisos de tudo o que já está assim: você recebe um resumo e, daí em diante, só os próximos.',
     `<div class="cfg-card"><h4>Tipos de aviso</h4>${['selo','novo','igual','24m'].map(t=>swRow('alerta.tipos.'+t,!!tp[t],TIPO_NOME[t],`${esc(TIPO_DESC[t])} · ${FREQ[t]}`)).join('')}</div>
     <div class="cfg-card"><h4>Limites</h4>
      ${row('Desconto mínimo','Vale para Novo recorde, Igual e Menor em 2 anos.',num('alerta.desconto_minimo',a.desconto_minimo,5,0,100,'%'))}
      ${row('Selo Kurokami: desconto mínimo','Corte só para o Selo.',num('alerta.selo_corte_minimo',a.selo_corte_minimo??0,5,0,100,'%'))}
      ${row('Tolerância acima do menor histórico','',num('alerta.tolerancia_pct',a.tolerancia_pct,1,0,50,'%'))}
      ${row('Modo completo: dias de observação','',num('alerta.dias_minimos_completo',a.dias_minimos_completo??14,1,0,365,'dias'))}
      <div class="cfg-nota">Análises da Steam não decidem avisos.</div></div>`)}
   ${sec('lojas','Lojas','O Hunter coleta todas as lojas; aqui você decide de quais pode vir um alerta.',
     `<div class="cfg-card">${swRow('somente_drm_steam',c.somente_drm_steam,'Só chave ativável na Steam','Só alerta quando a chave ativa na Steam (DRM Steam).')}
      ${row('Lojas que podem alertar',`<span id="ljN"></span>`,'<button class="btn-ghost" type="button" data-lj="1">Todas</button><button class="btn-ghost" type="button" data-lj="0">Nenhuma</button>')}
      <div class="cfg-lojas">${lojas.map(l=>`<label class="cfg-lj"><input type="checkbox" data-loja="${esc(l)}" ${marc.has(l.toLowerCase())?'checked':''}>${esc(l)}</label>`).join('')}</div></div>`)}
   ${sec('notif','Notificações','Os avisos aparecem no canto da tela do Windows. O histórico fica em Configurações → Notificações.',
     `<div class="cfg-card">${swRow('notificacoes.ativas',n.ativas!==false,'Notificar no Windows','')}
      ${row('Máximo por checagem','',num('notificacoes.max_por_rodada',n.max_por_rodada??5,1,1,20))}
      ${row('Avisar de novo se cair','Um jogo já avisado só avisa de novo se baixar pelo menos isto.',num('notificacoes.melhora_minima_reais',n.melhora_minima_reais??0.5,0.5,0,null,'R$',1))}
      ${row('Avisar quando a promoção estiver acabando','Vale para o que está no carrinho ou que avisa. 0 desliga.',num('notificacoes.termina_em_breve_horas',n.termina_em_breve_horas??24,1,0,168,'horas antes'))}
      ${row('Horário de silêncio','Sem notificações nesse intervalo (vale para o Windows e para o Telegram).',`${sw('notificacoes.silencio.ativo',si.ativo,'Horário de silêncio')}<span>de</span><input class="cfg-time" type="time" data-k="notificacoes.silencio.de" value="${esc(si.de||'23:00')}"><span>até</span><input class="cfg-time" type="time" data-k="notificacoes.silencio.ate" value="${esc(si.ate||'08:00')}">`)}</div>
`)}
   ${sec('telegram','Telegram','Os mesmos avisos no celular, de graça, por um bot seu do Telegram.',`<div class="cfg-card" id="tgBox">${tgHtml()}</div>`)}
   ${sec('freq','Frequência','De quanto em quanto tempo o Hunter busca preços. A primeira verificação é sempre completa.',
     `<div class="cfg-card"><h4>Verificação rápida</h4>
      ${row('Preços nas lojas (ITAD)',`A cada ${iv.itad} min e no "Verificar agora": preços em todas as lojas.`,num('intervalos_minutos.itad',iv.itad,5,10,null,'min'))}
      ${row('Keyshops (GG.deals)','A GG.deals só atualiza de hora em hora; menos que 60 não ajuda.',num('intervalos_minutos.ggdeals',iv.ggdeals,10,60,null,'min'))}
      ${row('Catálogo da Steam','',num('intervalos_minutos.steam',iv.steam,30,60,null,'min'))}</div>
     <div class="cfg-card"><h4>Verificação completa</h4>
      ${row('Fazer a completa a cada','Também catálogo da Steam, biblioteca, listas de DLC, edições, bundles e histórico, sem limite de ritmo. 0 = só quando você pedir.',num('verificacao_completa_dias',c.verificacao_completa_dias??7,1,0,90,'dias'))}
      ${row('Verificação completa agora','Acompanhe pelo status no topo.','<button class="btn-ghost" id="btnTudo" type="button">Começar agora</button>')}</div>`)}
   ${sec('steam','Steam inteira','Todas as promoções da Steam, além da sua lista (Ofertas → Promoções → Steam inteira).',
     `<div class="cfg-card">${swRow('steam_inteira',c.steam_inteira!==false,'Buscar todas as promoções da Steam','Não gera avisos: os avisos continuam só para a sua lista.')}
      ${row('Atualizar a cada','Também atualiza no "Verificar agora". Cada consulta substitui a anterior: ~1 MB num dia comum, ~16 MB e ~3 min em grande promoção.',num('intervalos_minutos.steam_inteira',iv.steam_inteira??60,15,30,1440,'min'))}</div>`)}
   ${sec('keyshops','Keyshops','Preços de lojas de chaves, via GG.deals. O preço de keyshop continua na ficha do jogo e no filtro "Keyshop bem mais barata".',
     `<div class="cfg-card">${swRow('keyshops.ativo',k.ativo,'Alertar keyshop quando estiver muito barata','Desligado por padrão: a GG.deals dava muito alarme falso.')}
      ${row('Abaixo de','',num('keyshops.preco_maximo',k.preco_maximo,1,0,null,'R$',1))}
      ${row('ou abaixo de','Porcentagem do menor preço oficial.',num('keyshops.pct_do_menor_oficial',k.pct_do_menor_oficial,5,0,100,'%'))}</div>`)}
   ${sec('dlc','DLCs','O que entra no custo completo de um jogo (jogo + DLCs). Cada DLC pode ser reclassificada na ficha do jogo.',
     `<div class="cfg-card">${swRow('dlc.ignorar_cosmeticos',dl.ignorar_cosmeticos,'Ignorar cosméticos','Skins, roupas, visuais.')}
      ${swRow('dlc.ignorar_extras',dl.ignorar_extras,'Ignorar extras','Trilha sonora, artbook.')}
      ${swRow('dlc.ignorar_atalhos',dl.ignorar_atalhos,'Ignorar atalhos e moedas','')}
      ${swRow('dlc.ignorar_pacotes',dl.ignorar_pacotes,'Ignorar pacotes que juntam outras DLCs','')}
      ${swRow('dlc.ignorar_gratis',dl.ignorar_gratis,'Ignorar DLCs gratuitas','')}</div>`)}
   ${sec('acesso','Celular e outros PCs','Abrir o painel pelo celular ou por outro computador da mesma rede Wi-Fi. Esta parte salva na hora.',
     `<div class="cfg-card"><div class="cfg-in" id="acesso">carregando…</div></div>`)}
   </div></div>
   <div class="cfg-save" id="cfgSaveBar" hidden><span>Alterações não salvas</span><button class="btn-ghost" id="cfgDesc" type="button">Descartar</button><button class="btn-go2" id="cfgSave" type="button">Salvar</button></div>`;
  const f=$('#cfgForm'),q=x=>[...f.querySelectorAll(x)];
  const mostrar=id=>{if(!CFG_SECOES.some(x=>x[0]===id))id='avisos';ls.set('cfgSec',id);
    q('.cfg-nav [data-sec]').forEach(b=>b.setAttribute('aria-selected',b.dataset.sec===id));q('.cfg-sec').forEach(x=>x.hidden=x.dataset.sec!==id);};
  mostrar(atual);
  f.querySelector('.cfg-nav').addEventListener('click',e=>{const b=e.target.closest('[data-sec]');if(b)mostrar(b.dataset.sec);});
  f.addEventListener('click',async e=>{const b=e.target.closest('[data-tg]');if(!b)return;
    const acao=b.dataset.tg,tg=(CFG.notificacoes=CFG.notificacoes||{}).telegram=CFG.notificacoes.telegram||{ativo:false,chat_id:''};
    b.disabled=true;const r=await post('/api/telegram',{acao,token:acao==='token'?$('#tgTok').value:undefined});b.disabled=false;
    if(!r.ok){toast(r.erro||'Erro');return;}
    if(acao==='token'){TGTOK=true;tg.chat_id='';tg.ativo=false;toast('Bot '+r.bot+' conectado');}
    else if(acao==='vincular'){tg.chat_id=r.chat_id;tg.ativo=true;toast('Vinculado a '+r.nome+'. Mandei uma mensagem para confirmar.');}
    else if(acao==='testar')toast('Mensagem enviada. Veja no Telegram.');
    else{TGTOK=false;tg.chat_id='';tg.ativo=false;toast('Telegram desconectado');}
    $('#tgBox').innerHTML=tgHtml();});
  const contaLojas=()=>{const t=q('[data-loja]');$('#ljN').textContent=`${t.filter(x=>x.checked).length} de ${t.length} marcadas`;};contaLojas();
  const sujo=()=>{$('#cfgSaveBar').hidden=false;};
  if(!f.dataset.ouvindo){f.dataset.ouvindo=1;  // #cfgForm fica; os ouvintes entram uma vez só (re-render e Descartar não somam)
  f.addEventListener('click',e=>{const b=e.target.closest('[data-lj]');if(!b)return;q('[data-loja]').forEach(x=>x.checked=b.dataset.lj==='1');contaLojas();sujo();});
  const mudou=e=>{if(e.target.closest('#acesso')||!e.target.matches('[data-k],[data-loja]'))return;if(e.target.dataset.loja!=null)contaLojas();sujo();};
  f.addEventListener('input',mudou);f.addEventListener('change',mudou);}
  $('#cfgSave').addEventListener('click',salvarCfg);$('#cfgDesc').addEventListener('click',()=>{renderCfg();toast('Alterações descartadas');});renderAcesso();
  $('#btnTudo').addEventListener('click',async()=>{const r=await post('/api/atualizar_tudo');if(r.ok)toast('Atualização completa começou. Acompanhe pelo status no topo.');});
}
async function renderAcesso(){
  let a;try{a=await api('/api/acesso');}catch(e){$('#acesso').innerHTML='<div class="hint">Só dá para configurar pelo próprio PC.</div>';return;}
  $('#acesso').innerHTML=`<label class="tick"><input type="checkbox" id="rl" ${a.rede_local?'checked':''}>Permitir abrir o painel por outros aparelhos da mesma rede Wi-Fi</label>
    ${a.rede_local?(a.links.length?`<div class="hint">No celular (mesmo Wi-Fi), abra o endereço ou leia o QR e digite o PIN uma vez. O aparelho fica lembrado.</div>
      <div class="lnk" style="font-size:15px">${esc(a.links[0])}</div><div class="tot"><span>PIN</span><b style="font-size:22px;letter-spacing:.2em;color:#fff">${esc(a.pin)}</b></div>
      <div class="qr" id="qr"></div>${a.links.length>1?`<div class="hint">Outros endereços deste PC: ${a.links.slice(1).map(esc).join(' · ')}</div>`:''}
      <button class="btn-ghost" id="novoCod" type="button">Trocar o PIN (desconecta os aparelhos liberados)</button>`:'<div class="hint">Não achei o endereço deste PC na rede.</div>'):
      '<div class="hint">Desligado: o painel só abre neste PC. Ao ligar, o Windows pode pedir permissão do firewall para o Python: escolha "Redes privadas".</div>'}`;
  $('#rl').addEventListener('change',async e=>{await post('/api/acesso',{rede_local:e.target.checked});toast(e.target.checked?'Liberado na rede local':'Só neste PC');setTimeout(renderAcesso,1500);});
  if($('#novoCod'))$('#novoCod').addEventListener('click',async()=>{await post('/api/acesso',{novo_codigo:true});toast('Código novo gerado');renderAcesso();});
  if(a.rede_local&&a.links.length&&$('#qr')){const desenhar=()=>{try{new QRCode($('#qr'),{text:a.links[0],width:160,height:160});}catch(e){}};
    comQR(desenhar);}
}
function setPath(o,p,v){const k=p.split('.');let x=o;k.slice(0,-1).forEach(s=>{x[s]=x[s]||{};x=x[s];});x[k[k.length-1]]=v;}
async function salvarCfg(){
  const c=JSON.parse(JSON.stringify(CFG));
  $$('#cfgForm [data-k]').forEach(el=>{const v=el.type==='checkbox'?el.checked:(el.type==='number'||el.dataset.num)?(el.value===''?0:+el.value):el.value;setPath(c,el.dataset.k,v);});
  c.lojas=$$('#cfgForm [data-loja]').filter(el=>el.checked).map(el=>el.dataset.loja);
  const r=await post('/api/config',{config:c});toast(r.ok?'Salvo. Vale a partir da próxima checagem (use "Verificar agora").':'Erro: '+(r.erro||'?'));
  if(r.ok){CFG=c;$('#cfgSaveBar').hidden=true;}
}
