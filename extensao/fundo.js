// Kurokami Radar: faz as duas chamadas do carrinho da conta (ler e adicionar) para a pagina do carrinho da Steam.
// Fica aqui (e nao na pagina) porque a extensao pode chamar api.steampowered.com sem esbarrar no CORS.
// O token vem da propria pagina da Steam e so vai para a Steam; nada e guardado.
const METODOS = { GetCart: 'GET', AddItemsToCart: 'POST' };

chrome.runtime.onMessage.addListener((msg, remetente, responder) => {
  if (!(msg && Object.hasOwn(METODOS, msg.metodo)) || !String(remetente.url || '').startsWith('https://store.steampowered.com/')) return;
  const url = `https://api.steampowered.com/IAccountCartService/${msg.metodo}/v1/`;
  const params = new URLSearchParams({ access_token: msg.token, input_json: JSON.stringify(msg.entrada) });
  const pedido = METODOS[msg.metodo] === 'POST' ? fetch(url, { method: 'POST', body: params }) : fetch(url + '?' + params);
  pedido.then(r => (r.ok ? r.json() : Promise.reject(new Error('a Steam respondeu ' + r.status))))
    .then(j => responder({ ok: true, r: (j && j.response) || {} }), e => responder({ ok: false, erro: String(e.message || e) }));
  return true;   // responde depois (assincrono)
});
