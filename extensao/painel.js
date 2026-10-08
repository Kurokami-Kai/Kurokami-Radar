// Kurokami Radar: marca no painel (localhost) que a extensao esta instalada e entrega ao Radar, uma vez por leitura,
// os dados da conta que conta.js guardou na loja da Steam. O painel avisa o resultado pelo evento "kurokami-conta".
if (location.pathname.startsWith('/kurokami')) {
  document.documentElement.dataset.kurokamiExt = chrome.runtime.getManifest().version;
  chrome.storage.local.get(['kurokami_conta', 'kurokami_entregue']).then(async s => {
    const c = s.kurokami_conta;
    if (!c || c.quando === s.kurokami_entregue) return;
    let j;
    try {
      const r = await fetch('/api/steam/conta', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c) });
      j = await r.json();
    } catch (e) { return; }   // Radar fechado ou antigo: tenta na proxima abertura
    if (j && j.ok) await chrome.storage.local.set({ kurokami_entregue: c.quando });   // erro (perfil, outra conta): tenta de novo
    document.dispatchEvent(new CustomEvent('kurokami-conta', { detail: JSON.stringify(j || {}) }));
  }).catch(() => {});
}
