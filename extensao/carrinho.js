// Kurokami Hunter: poe no carrinho da Steam o pedido que o painel mandou no endereco
// (store.steampowered.com/cart/#kurokami=BR:p123,b456-presente,p789-privado).
// Usa a sessao que a propria pagina da Steam ja tem; o token nunca sai deste navegador nem vai para o Hunter.
// So adiciona o que ainda nao esta no carrinho (em qualquer modo) e confere lendo de volta; nunca remove nada.
(() => {
  const PENDENTE = 'kurokami_pedido', AVISO = 'kurokami_aviso', VALIDADE = 15 * 60 * 1000;
  const FLAGS = { presente: { is_gift: true }, privado: { is_private: true } };

  function faixa(texto, tipo, link) {
    let d = document.getElementById('kurokami-faixa');
    if (!d) {
      d = document.createElement('div');
      d.id = 'kurokami-faixa';
      d.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;padding:10px 16px;font:13px "Motiva Sans",Arial,sans-serif;' +
        'text-align:center;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.5)';
      d.onclick = e => { if (e.target === d) d.remove(); };
      document.body.appendChild(d);
    }
    d.style.background = tipo === 'erro' ? '#8b2f22' : tipo === 'aviso' ? '#7a5a12' : tipo === 'ok' ? '#4c6b22' : '#1f1f1f';
    d.textContent = 'Kurokami Hunter: ' + texto;
    if (link) {
      const a = document.createElement('a');
      a.href = link.href;
      a.textContent = link.texto;
      a.style.cssText = 'color:#fff;font-weight:bold;margin-left:10px;text-decoration:underline';
      d.appendChild(a);
    }
  }

  function lerPedido() {
    const m = location.hash.match(/kurokami=([^&]+)/);
    if (m) {
      history.replaceState(null, '', location.pathname + location.search);   // recarregar nao repete o pedido
      const [pais, lista] = decodeURIComponent(m[1]).split(':');
      const itens = (lista || '').split(',').map(t => t.match(/^([pb])(\d+)(?:-(presente|privado))?$/)).filter(Boolean)
        .map(x => ({ tipo: x[1] === 'p' ? 'pacote' : 'bundle', id: +x[2], modo: x[3] || 'conta' }));
      return { pais: /^[A-Z]{2}$/.test(pais) ? pais : 'BR', itens, quando: Date.now() };
    }
    try {   // pedido que esperava o login (a Steam volta para o carrinho sem o #)
      const p = JSON.parse(sessionStorage.getItem(PENDENTE) || 'null');
      if (p && Date.now() - p.quando < VALIDADE) return p;
    } catch (e) { /* sessionStorage indisponivel */ }
    return null;
  }

  async function tokenDaPagina() {
    try {
      const c = JSON.parse((document.getElementById('application_config') || {}).dataset.store_user_config || '{}');
      if (c.webapi_token) return c.webapi_token;
    } catch (e) { /* pagina sem a configuracao embutida */ }
    try {
      const j = await (await fetch('/pointssummary/ajaxgetasyncconfig', { credentials: 'include' })).json();
      if (j && j.data && j.data.webapi_token) return j.data.webapi_token;
    } catch (e) { /* sem sessao */ }
    return null;
  }

  async function steam(metodo, entrada, token) {
    const r = await chrome.runtime.sendMessage({ metodo, entrada, token });
    if (!r || !r.ok) throw new Error((r && r.erro) || 'sem resposta da extensão');
    return r.r;
  }

  const chave = i => (i.tipo ? i.tipo + ':' + i.id : i.bundleid ? 'bundle:' + i.bundleid : 'pacote:' + i.packageid);

  async function rodar() {
    try {
      const a = JSON.parse(sessionStorage.getItem(AVISO) || 'null');
      sessionStorage.removeItem(AVISO);
      if (a) faixa(a.texto, a.tipo);
    } catch (e) { /* sem aviso guardado */ }
    const ped = lerPedido();
    if (!ped || !ped.itens.length) return;
    const token = await tokenDaPagina();
    if (!token) {
      try { sessionStorage.setItem(PENDENTE, JSON.stringify(ped)); } catch (e) { /* segue sem guardar */ }
      faixa('entre na sua conta Steam; os ' + ped.itens.length + ' item(ns) do pedido entram no carrinho logo depois.', 'aviso',
        { href: '/login/?redir=cart%2F', texto: 'Entrar' });
      return;
    }
    try { sessionStorage.removeItem(PENDENTE); } catch (e) { /* nada */ }
    faixa('colocando ' + ped.itens.length + ' item(ns) no carrinho…');
    try {
      const ler = async () => (((await steam('GetCart', { user_country: ped.pais }, token)).cart || {}).line_items) || [];
      const antes = new Set((await ler()).map(chave));
      const novos = ped.itens.filter(i => !antes.has(chave(i)));
      if (novos.length) {
        const items = novos.map(i => Object.assign(i.tipo === 'pacote' ? { packageid: i.id } : { bundleid: i.id },
          FLAGS[i.modo] ? { flags: FLAGS[i.modo] } : {}));
        await steam('AddItemsToCart', { user_country: ped.pais, items }, token);
      }
      const modoDa = l => (l.flags && l.flags.is_gift ? 'presente' : l.flags && l.flags.is_private ? 'privado' : 'conta');
      const depois = new Map((await ler()).map(l => [chave(l), modoDa(l)]));
      const faltaram = novos.filter(i => !depois.has(chave(i))).length;
      const outroModo = novos.filter(i => depois.has(chave(i)) && depois.get(chave(i)) !== i.modo).length;
      const ja = ped.itens.length - novos.length;
      const texto = (novos.length - faltaram) + ' item(ns) novo(s) no carrinho' +
        (ja ? ' (' + ja + ' já estava(m) aqui e não foi(ram) repetido(s))' : '') +
        (faltaram ? '. ' + faltaram + ' não entrou(aram): a Steam pode não vender esse item na sua região ou você já o tem' : '') +
        (outroModo ? '. ' + outroModo + ' entrou(aram) sem o modo pedido (presente/privado): ajuste aqui no carrinho' : '') +
        (faltaram || outroModo ? '.' : '. Confira e conclua o pagamento.');
      const aviso = { texto, tipo: faltaram || outroModo ? 'aviso' : 'ok' };
      if (novos.length - faltaram > 0) {   // recarrega para a pagina mostrar os itens novos
        try { sessionStorage.setItem(AVISO, JSON.stringify(aviso)); } catch (e) { /* recarrega sem a faixa */ }
        location.reload();
      } else faixa(aviso.texto, aviso.tipo);
    } catch (e) {
      faixa('não consegui colocar no carrinho (' + e.message + '). Clique em Finalizar pedido no painel de novo.', 'erro');
    }
  }

  rodar();
})();
