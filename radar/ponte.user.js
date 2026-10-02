// ==UserScript==
// @name         Kurokami Radar - ponte com a Steam
// @namespace    kurokami-radar
// @version      1.1.0
// @updateURL    http://localhost/kurokami/ponte.user.js
// @downloadURL  http://localhost/kurokami/ponte.user.js
// @description  Leva o carrinho do Kurokami Radar para o carrinho da Steam e aplica as mudancas de lista de desejos feitas no painel. Usa o seu login da Steam so dentro do navegador; nada sai do seu PC.
// @match        https://store.steampowered.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_openInTab
// @grant        unsafeWindow
// @connect      localhost
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';
  const BASES = ['http://localhost', 'http://localhost:8787'];
  let BASE = null;

  // ---------------------------------------------------------------- conversa com o Radar (no seu PC)
  function radar(metodo, caminho, dados) {
    return new Promise((ok, falha) => {
      GM_xmlhttpRequest({
        method: metodo, url: BASE + caminho, timeout: 8000,
        headers: { 'Content-Type': 'application/json' },
        data: dados ? JSON.stringify(dados) : undefined,
        onload: r => { try { ok(JSON.parse(r.responseText)); } catch (e) { falha(e); } },
        onerror: falha, ontimeout: falha,
      });
    });
  }
  async function acharRadar() {
    for (const b of BASES) {
      BASE = b;
      try { const r = await radar('GET', '/api/ponte'); if (r && r.ok) return r; } catch (e) { /* tenta a proxima porta */ }
    }
    return null;
  }

  // ---------------------------------------------------------------- Steam (mesma origem: usa o seu login)
  const sessao = () => (unsafeWindow.g_sessionID) || (document.cookie.match(/sessionid=([^;]+)/) || [])[1];
  const logado = () => !!(unsafeWindow.g_AccountID || document.querySelector('#account_pulldown'));

  async function postSteam(url, campos) {
    const f = new FormData();
    Object.entries(campos).forEach(([k, v]) => f.append(k, v));
    const r = await fetch(url, { method: 'POST', body: f, credentials: 'include' });
    let j = null;
    try { j = await r.clone().json(); } catch (e) { /* algumas respostas sao HTML */ }
    return { ok: r.ok, json: j };
  }

  async function listaDesejos(fila) {
    const feitos = [];
    for (const it of fila) {
      const url = it.acao === 'remove' ? '/api/removefromwishlist' : '/api/addtowishlist';
      try {
        const r = await postSteam('https://store.steampowered.com' + url, { sessionid: sessao(), appid: it.appid });
        feitos.push({ appid: it.appid, acao: it.acao, ok: !!(r.json && r.json.success) });
      } catch (e) {
        feitos.push({ appid: it.appid, acao: it.acao, ok: false });
      }
    }
    return feitos;
  }

  async function addCarrinho(it) {
    if (it.tipo !== 'bundle' && !it.subid) return 'o Radar ainda não sabe o pacote (rode "Atualizar tudo")';
    const campos = { action: 'add_to_cart', sessionid: sessao() };
    if (it.tipo === 'bundle') campos.bundleid = it.bundleid; else campos.subid = it.subid;
    try {
      const r = await postSteam('https://store.steampowered.com/cart/addtocart', campos);
      if (r.ok && (!r.json || r.json.success !== false)) return null;
      console.warn('[Kurokami] Steam recusou', it, r);
      return 'a Steam recusou (HTTP ' + (r.ok ? 'ok, success=false' : 'erro') + ')';
    } catch (e) {
      console.warn('[Kurokami] falha de rede', it, e);
      return 'falha de rede';
    }
  }

  // ---------------------------------------------------------------- verificacao de idade
  // Jogos com classificacao 16/18 abrem uma tela "confirme sua idade" no lugar da pagina; sem passar
  // por ela nao existe botao de comprar. A Steam guarda a resposta nestes cookies.
  function liberarIdade() {
    const exp = '; path=/; max-age=31536000; secure; samesite=lax';
    if (!/birthtime=/.test(document.cookie)) document.cookie = 'birthtime=631152001' + exp;
    if (!/lastagecheckage=/.test(document.cookie)) document.cookie = 'lastagecheckage=1-0-1990' + exp;
    if (!/wants_mature_content=/.test(document.cookie)) document.cookie = 'wants_mature_content=1' + exp;
  }
  function passarTelaDeIdade() {
    if (!location.pathname.startsWith('/agecheck/')) return false;
    const ano = document.getElementById('ageYear');
    if (ano) ano.value = '1990';
    if (typeof unsafeWindow.ViewProductPage === 'function') { unsafeWindow.ViewProductPage(); return true; }
    const btn = document.querySelector('#view_product_page_btn, a.btnv6_blue_hoverfade');
    if (btn) { btn.click(); return true; }
    return false;
  }

  // ---------------------------------------------------------------- plano B: clicar no botao da pagina
  function planoB() {
    const m = (location.hash + '|' + (sessionStorage.getItem('kr_add') || '')).match(/kr_add=(sub|bundle)(\d+)/);
    if (!m) return;
    sessionStorage.setItem('kr_add', 'kr_add=' + m[1] + m[2]);  // sobrevive ao redirecionamento da tela de idade
    if (passarTelaDeIdade()) return;
    const campo = m[1] === 'sub' ? 'subid' : 'bundleid';
    const inp = document.querySelector(`input[name="${campo}"][value="${m[2]}"]`);
    let form = inp && inp.closest('form');
    if (!form && m[1] === 'sub') form = document.querySelector(`form[name="add_to_cart_${m[2]}"]`);
    sessionStorage.removeItem('kr_add');
    if (form) { aviso('Kurokami: adicionando ao carrinho…'); form.submit(); }
    else {
      aviso('Kurokami: não achei o botão desse item nesta página. Clique em "Adicionar ao carrinho" você mesmo.', true);
      console.warn('[Kurokami] plano B sem formulario para', m[1], m[2], location.href);
    }
  }

  // ---------------------------------------------------------------- interface
  function aviso(txt, erro) {
    let el = document.getElementById('kr-aviso');
    if (!el) {
      el = document.createElement('div');
      el.id = 'kr-aviso';
      el.style.cssText = 'position:fixed;left:20px;bottom:20px;z-index:99999;background:#171a21;color:#c7d5e0;padding:10px 14px;' +
        'font:13px Arial;box-shadow:0 4px 18px #000a;border-left:3px solid #66c0f4;max-width:360px';
      document.body.appendChild(el);
    }
    el.style.borderLeftColor = erro ? '#d6492f' : '#66c0f4';
    el.textContent = txt;
    clearTimeout(el._t);
    el._t = setTimeout(() => el.remove(), 7000);
  }

  function botao(itens) {
    if (!itens.length || document.getElementById('kr-btn')) return;
    const b = document.createElement('button');
    b.id = 'kr-btn';
    b.textContent = `Trazer o carrinho do Kurokami Radar (${itens.length})`;
    b.style.cssText = 'position:fixed;right:20px;bottom:20px;z-index:99999;border:0;cursor:pointer;color:#fff;padding:11px 16px;' +
      'font:14px Arial;border-radius:2px;background:linear-gradient(90deg,#75b022 5%,#588a1b 95%);box-shadow:0 4px 18px #000a';
    b.onclick = async () => {
      if (!logado()) { aviso('Entre na sua conta Steam primeiro.', true); return; }
      b.disabled = true;
      let ok = 0;
      const falhou = [];
      liberarIdade();
      for (const it of itens) {
        b.textContent = `Adicionando ${ok + falhou.length + 1} de ${itens.length}…`;
        const motivo = await addCarrinho(it);
        if (motivo) falhou.push(Object.assign({ motivo }, it)); else ok++;
      }
      // o que nao entrou pela via direta abre na pagina do item, onde a ponte clica no botao
      falhou.forEach(it => GM_openInTab(it.url + (it.subid ? '#kr_add=sub' + it.subid : it.bundleid ? '#kr_add=bundle' + it.bundleid : ''), { active: false }));
      try {
        await radar('POST', '/api/ponte/feito', { carrinho: { enviados: ok, falhas: falhou.length,
          itens_falhos: falhou.map(f => ({ nome: f.nome, appid: f.appid, bundleid: f.bundleid, subid: f.subid, motivo: f.motivo })) } });
      } catch (e) { /* so registro */ }
      aviso(falhou.length ? `${ok} no carrinho. ${falhou.length} abriram em abas para concluir.` : `${ok} item(ns) no carrinho da Steam.`);
      setTimeout(() => { location.href = 'https://store.steampowered.com/cart/'; }, 1500);
    };
    document.body.appendChild(b);
  }

  // ---------------------------------------------------------------- inicio
  (async () => {
    liberarIdade();
    planoB();
    const d = await acharRadar();
    if (!d) return; // Radar fechado: a ponte fica quieta
    if (d.fila && d.fila.length && logado()) {
      const feitos = await listaDesejos(d.fila);
      try { await radar('POST', '/api/ponte/feito', { lista: feitos }); } catch (e) { /* tenta de novo na proxima pagina */ }
      const bons = feitos.filter(f => f.ok).length;
      aviso(`Kurokami: ${bons} mudança(s) aplicadas na sua lista de desejos` + (bons < feitos.length ? `, ${feitos.length - bons} falharam.` : '.'), bons < feitos.length);
    }
    if (!location.pathname.startsWith('/cart')) botao(d.carrinho || []);
  })();
})();
