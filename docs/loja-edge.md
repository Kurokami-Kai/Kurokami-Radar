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

  - Só age na página do carrinho da Steam (store.steampowered.com/cart) e só quando o pedido vem do Hunter.
  - Usa a sessão que o seu navegador já tem na Steam. Não pede senha, não guarda nada e não envia nada a ninguém além da própria Steam.
  - Só adiciona: nunca remove nem altera o que já estava no seu carrinho, e não repete o que já está lá.
  - Não tem anúncios nem rastreamento.

  Sem o Kurokami Hunter instalado, a extensão não faz nada.
- **Logo da loja:** `output/loja-edge-logo-300.png`.
- **Capturas de tela (opcional):** a aba Carrinho do Hunter e a faixa "Kurokami Hunter: … no carrinho" na Steam (1280x800).
- **Política de privacidade (URL):** https://github.com/Kurokami-Kai/Kurokami-Hunter/blob/main/docs/privacidade-extensao.md
- **Site:** https://github.com/Kurokami-Kai/Kurokami-Hunter
- **Justificativa das permissões** (se perguntarem):
  - *Acesso a store.steampowered.com/cart:* ler o pedido do endereço e mostrar o resultado na página do carrinho.
  - *Acesso a api.steampowered.com:* ler e adicionar itens ao carrinho da conta (IAccountCartService), com o token que a própria página da Steam já tem.
  - *Acesso a localhost:* só marca no painel local do Hunter que a extensão está instalada; não lê nem envia nada.
- **Notas para a certificação:** "Para testar: em store.steampowered.com, logado, abra https://store.steampowered.com/cart/#kurokami=BR:p<subid> (o subid de um jogo pago, que aparece no botão "Adicionar ao carrinho" da página do jogo). A extensão adiciona o item ao carrinho e mostra uma faixa no topo. Sem o fragmento #kurokami, ela não faz nada."

## Depois de aprovada
Mande ao Claude o link da extensão na loja (`https://microsoftedge.microsoft.com/addons/detail/<id>`): o assistente do Hunter passa a abrir a loja no Edge (um clique em "Obter") e mantém o "Carregar sem compactação" para os outros navegadores.

Atualizar: suba `version` em `extensao/manifest.json`, gere o ZIP de novo e envie como nova versão no Partner Center.
