# Extensão na loja do Edge (Microsoft Partner Center)

Roteiro para o dono publicar a extensão do carrinho. O pacote sai de `py tools/gerar_extensao.py` (pasta `output/`, fora do Git).

## Antes
1. Conta de desenvolvedor do Edge (grátis): https://partner.microsoft.com/dashboard/microsoftedge/overview, com a sua conta Microsoft. Nome do editor: o que deve aparecer na loja (ex.: "Kurokami").
2. `py tools/gerar_extensao.py` → `output/kurokami-radar-extensao-<versão>.zip` e `output/loja-edge-logo-300.png`.

O `description` do `manifest.json` tem no máximo **132 caracteres** (a loja recusa o pacote acima disso; o `checar.py` confere).

## Formulário
- **Pacote:** o ZIP acima.
- **Disponibilidade:** "Oculto" (só quem tem o link instala; o Hunter abre o link) ou "Público". Mercados: todos, ou só Brasil.
- **Categoria:** Compras (Shopping).
- **Idioma da página:** Português (Brasil).
- **Nome:** Kurokami Hunter - carrinho da Steam
- **Descrição curta:** Coloca no carrinho da Steam os jogos separados no Kurokami Hunter, com um clique em Finalizar pedido.
- **Descrição:**

  Complemento do Kurokami Hunter (app de Windows que acompanha os preços da sua lista de desejos da Steam).

  Na aba Carrinho do Hunter, você separa os jogos que quer comprar e escolhe se cada um é para a sua conta, de presente ou privado. Ao clicar em "Finalizar pedido", o Hunter abre o carrinho da Steam e esta extensão coloca os jogos lá, sem você precisar abrir a página de cada um.

  - No carrinho da Steam (store.steampowered.com/cart), só age quando o pedido vem do Hunter.
  - Na loja da Steam, lê com a sua sessão o que a conta tem, deseja, segue e ignora e entrega ao Hunter no seu PC (localhost), para ele não sugerir o que você já tem ou ignorou.
  - Não pede senha, não guarda token nem cookie, e nada sai do seu PC a não ser para a própria Steam.
  - Só adiciona: nunca remove nem altera o que já estava no seu carrinho, e não repete o que já está lá.
  - Não tem anúncios nem rastreamento.

  Sem o Kurokami Hunter instalado, a extensão não faz nada.
- **Logo da loja:** `output/loja-edge-logo-300.png`.
- **Capturas de tela (opcional):** a aba Carrinho do Hunter e a faixa "Kurokami Hunter: … no carrinho" na Steam (1280x800).
- **Política de privacidade (URL):** https://github.com/Kurokami-Kai/Kurokami-Radar/blob/main/docs/privacidade-extensao.md (o repositório continua com o nome antigo; o link com "Kurokami-Hunter" dá 404)
- **Site:** https://github.com/Kurokami-Kai/Kurokami-Radar
- **Permission justification** (o formulário é em inglês; cole como está):
  - *storage justification:* Stores, only in this browser (chrome.storage.local), the app IDs that the user's Steam account owns, wishlists, follows, ignores and has in the cart, plus the SteamID, read from the Steam store page with the page's own session (at most once every 10 minutes). The Kurokami Hunter desktop app on the same PC (http://localhost) picks them up so it does not recommend games the user already owns or ignored. No password, token or cookie is stored, and nothing is sent anywhere except Steam and the local app.
  - *Host permission justification:* api.steampowered.com: the background worker calls IAccountCartService (GetCart and AddItemsToCart) to add the games chosen in the Kurokami Hunter app to the user's Steam cart; it runs in the extension because the Steam page cannot call this API directly (CORS). The access token comes from the Steam page itself and is sent only to Steam. store.steampowered.com: content scripts read the order on the cart page (#kurokami=...) and the account lists from /dynamicstore/userdata/. localhost and 127.0.0.1: the Kurokami Hunter dashboard running on the user's own PC; the extension marks that it is installed and hands over the lists above. No other sites.
  - *Are you using remote code?* No. (Justification em branco.)
- **Data usage:** nenhuma caixa marcada. Esses campos são sobre dados que o desenvolvedor coleta, e nada sai do PC do usuário (só vai à Steam e ao Hunter no mesmo PC); a política de privacidade descreve o que é lido. Marque as três declarações do fim do formulário (não vende nem transfere dados, não usa para outro fim, não usa para crédito).
- **Availability:** Hidden; mercados: todos.
- **Notas para a certificação:** "Para testar: em store.steampowered.com, logado, abra https://store.steampowered.com/cart/#kurokami=BR:p<subid> (o subid de um jogo pago, que aparece no botão "Adicionar ao carrinho" da página do jogo). A extensão adiciona o item ao carrinho e mostra uma faixa no topo. Sem o fragmento #kurokami, ela não faz nada."

## Depois de aprovada
Publicada em 10/10/2026: `LOJA_EDGE` em `radar/painel.py` guarda o link (`https://microsoftedge.microsoft.com/addons/detail/kurokami-hunter-carrinh/hkoneojejphjfakoapjjnjbgabcnljpl`). Com o Edge como navegador padrão, a faixa de instalação do painel abre a loja (um clique em "Obter"); "Instalar pela pasta" e os outros navegadores seguem com "Carregar sem compactação".

Atualizar: suba `version` em `extensao/manifest.json`, gere o ZIP de novo e envie como nova versão no Partner Center.
