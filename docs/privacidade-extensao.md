# Política de privacidade — Kurokami Hunter (extensão "carrinho da Steam")

Última atualização: 09/10/2026.

**Nada sai do seu computador, a não ser para a própria Steam.** A extensão não tem servidor, anúncios, analytics nem rastreamento, e não vende nem compartilha dados.

O que ela lê e para onde vai:

- **Carrinho da Steam** (`store.steampowered.com/cart`): quando o endereço traz um pedido do Kurokami Hunter (`#kurokami=…`), a extensão adiciona os pacotes do pedido ao seu carrinho. Para isso usa o token de sessão que a própria página da Steam já carregou e o envia **somente à Steam** (`api.steampowered.com`). O token não é guardado e não vai para nenhum outro lugar. Sem login, o pedido fica na memória da aba (`sessionStorage`) por até 15 minutos e é apagado.
- **Sua conta na loja da Steam** (`store.steampowered.com`): com a sessão da página, a extensão lê a lista de jogos que a conta tem, deseja, segue, ignora e tem no carrinho (só os números dos jogos) e o SteamID da conta logada. Guarda isso **só neste navegador** (`chrome.storage.local`), no máximo uma vez a cada 10 minutos.
- **Kurokami Hunter no seu PC** (`localhost`): ao abrir o painel do Hunter, a extensão marca que está instalada e entrega a ele essas listas, para o Hunter não sugerir jogos que você já tem ou ignorou. O Hunter guarda o arquivo no seu PC.

Senha, cookie e token da Steam nunca são guardados pela extensão nem enviados ao Hunter.

Para apagar: remova a extensão (o que ela guardou no navegador vai junto).

Dúvidas: https://github.com/Kurokami-Kai/Kurokami-Radar/issues
