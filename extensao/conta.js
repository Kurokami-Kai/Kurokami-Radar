// Kurokami Hunter: em qualquer pagina da loja da Steam, le (com a sessao da propria pagina) o que a sua conta tem:
// biblioteca com DLCs, lista de desejos, seguidos, ignorados e carrinho. Guarda so neste navegador; o painel do
// Hunter (localhost) busca daqui ao abrir. Senha, token e cookie nunca saem da Steam.
(async () => {
  const CHAVE = 'kurokami_conta', INTERVALO = 10 * 60 * 1000;
  let info = {};
  try { info = JSON.parse((document.getElementById('application_config') || {}).dataset.userinfo || '{}'); } catch (e) { /* pagina sem a configuracao */ }
  const steamid = String(info.steamid || '');
  if (!info.logged_in || !/^\d{17}$/.test(steamid)) return;
  try {
    const ant = (await chrome.storage.local.get(CHAVE))[CHAVE];
    if (ant && ant.steamid === steamid && Date.now() - ant.quando < INTERVALO) return;
    const r = await fetch('/dynamicstore/userdata/', { credentials: 'include', cache: 'no-store' });
    if (!r.ok) return;
    const u = await r.json();
    const ids = v => (Array.isArray(v) ? v : Object.keys(v || {})).map(Number).filter(n => Number.isInteger(n) && n > 0);
    if (!ids(u.rgOwnedApps).length) return;   // sessao ainda sem dados (a Steam as vezes devolve vazio)
    await chrome.storage.local.set({ [CHAVE]: {
      steamid, quando: Date.now(), possuidos: ids(u.rgOwnedApps), desejos: ids(u.rgWishlist),
      seguidos: ids(u.rgFollowedApps), ignorados: ids(u.rgIgnoredApps), carrinho: ids(u.rgAppsInCart) } });
  } catch (e) { /* sem rede ou a Steam mudou o formato: tenta na proxima pagina */ }
})();
