# Kurokami Hunter

Monitora a sua **lista de desejos da Steam** em dezenas de lojas, guarda o **histórico de preços** no seu PC e avisa pela **central de notificações do Windows** quando um jogo chega no menor preço em muito tempo (Selo Kurokami) ou nos tipos de recorde que você escolher. Tem um painel no navegador com lista, biblioteca de colecionador, carrinho simulado com bundles e acesso pelo celular.

Tudo roda no seu PC. Nada é enviado para servidor nenhum além das consultas às lojas (Steam, IsThereAnyDeal e GG.deals).

---

## 1. Instalar

1. Baixe o **`KurokamiRadar_Setup_vX.exe`** na página **Releases** deste repositório.
2. Abra o arquivo. Se o Windows mostrar *"O Windows protegeu o computador"*, clique em **Mais informações → Executar assim mesmo** (o programa não tem assinatura digital paga).
3. Siga o instalador. Não precisa de administrador nem de Python.

No fim, o Hunter abre sozinho e mostra a janela **Perfil e chaves**. É só preencher como explicado abaixo.

---

## 2. O que você precisa preencher

| Campo | Obrigatório? | Para que serve |
|---|---|---|
| Perfil Steam | **sim** | saber qual lista de desejos e biblioteca olhar |
| Chave da IsThereAnyDeal | **sim** | preços de dezenas de lojas e histórico |
| Chave da GG.deals | não | preços de keyshops na ficha do jogo e nos filtros (o aviso de keyshop vem desligado; dá para ligar em Configurações) |
| Chave da Steam Web API | não | ler a biblioteca quando você não tem o `userdata.json` |

As chaves ficam guardadas no **Gerenciador de Credenciais do Windows** (nunca num arquivo). Dá para trocar depois pelo menu do ícone: **Chaves e perfil…**

### Perfil Steam

1. Abra o seu perfil na Steam (no app: clique no seu nome → *Perfil*; no navegador: steamcommunity.com/my/profile).
2. Copie o endereço. Fica como `https://steamcommunity.com/id/seunome` ou `https://steamcommunity.com/profiles/7656119...`.
3. Cole no campo **Seu perfil Steam**.

**Ou entre pela Steam** (como no ITAD ou na SteamDB): no painel, botão *Entrar pela Steam* no canto superior direito (em qualquer aba); depois de entrar, ali fica o seu avatar (ver perfil, trocar de conta). Você confirma na página da própria Steam e o Hunter só recebe o seu SteamID: nunca a senha, nem token, nem cookie. Só funciona abrindo o painel no próprio PC.

**Carrinho direto (extensão do Hunter):** na aba Carrinho, *Finalizar pedido* abre o carrinho da Steam e a extensão do Hunter põe os jogos lá sozinha, com a sessão que o seu navegador já tem (o Hunter nunca vê senha, token ou cookie). Instale a extensão uma vez (Chrome, Edge, Brave ou Opera): ao abrir o painel, o Hunter pergunta se quer instalar e, em *Instalar*, abre a página de extensões e a pasta; ligue o *Modo do desenvolvedor* e arraste a pasta para a página. À mão: abra `chrome://extensions` (no Edge, `edge://extensions`), ligue o *Modo do desenvolvedor*, clique em *Carregar sem compactação* e escolha a pasta `extensao` da instalação do Hunter. Ela só age na página do carrinho da Steam e só adiciona: nunca tira nada.

**A lista de desejos precisa estar pública.** Na Steam: *Perfil → Editar perfil → Configurações de privacidade → Detalhes dos jogos = Público*. Se estiver privada, a janela avisa "a lista de desejos veio vazia".

### Chave da IsThereAnyDeal (obrigatória, gratuita)

1. Crie uma conta em **isthereanydeal.com** (canto superior direito, *Sign in*).
2. Acesse **isthereanydeal.com/apps/my** e clique para **registrar um app**. O nome pode ser qualquer um (ex.: `Kurokami Hunter`).
3. Na página do app, copie o campo **API Key**.
   ⚠️ Não é o *OAuth Client ID* nem o *Client Secret*.
4. Cole no campo **IsThereAnyDeal**.

### Chave da GG.deals (opcional, gratuita)

1. Crie uma conta em **gg.deals** e confirme o e-mail.
2. Acesse **gg.deals/settings**, seção **Connections**, e copie a **GG.deals API key**.
3. Cole no campo **GG.deals**.

### Chave da Steam Web API (opcional, gratuita)

Só faz diferença se você **não** usar o `userdata.json` (próxima seção).

1. Acesse **steamcommunity.com/dev/apikey** logado na Steam.
2. Em *Domain Name*, escreva qualquer coisa (ex.: `localhost`), aceite os termos e clique em *Register*.
3. Copie a **Key** (32 letras e números) e cole no campo **Steam Web API**.

Clique em **Salvar**. Cada campo é testado na hora: ✓ em branco está certo; ✗ vermelho mostra o motivo.

---

## 3. Opcional: suas DLCs, seguidos e ignorados (`userdata.json`)

A Steam só informa publicamente os **jogos** que você tem, não as **DLCs**, nem os jogos que você **segue** ou **ignorou** na loja. Sem isso, o Hunter não sabe quais DLCs você já comprou (afeta a aba Biblioteca e o preço de bundles) e os filtros "Seguido" e "Ignorado" de Promoções ficam desligados.

**Jeito automático (recomendado):** com a extensão do Hunter instalada (a mesma do carrinho, versão 1.1 ou mais nova), abra qualquer página da loja da Steam logado e depois o painel. A extensão lê esses dados com a sessão do próprio navegador (o Hunter nunca vê senha, token ou cookie) e o Hunter guarda no `userdata.json`. Só vale se a conta aberta no navegador for a do seu perfil no Hunter. Se você já tinha a extensão, recarregue-a em `chrome://extensions` depois de atualizar o Hunter.

**Jeito manual:**

1. No navegador, **logado na Steam**, abra: `https://store.steampowered.com/dynamicstore/userdata/`
2. Aparece um texto grande. Salve com **Ctrl+S** com o nome **`userdata.json`**.
3. Coloque o arquivo em `%LOCALAPPDATA%\Kurokami Radar` (cole esse endereço na barra do Explorador). Ou use o menu do ícone: **Abrir pasta dos dados**.

Repita de vez em quando: o painel avisa quando o arquivo tiver mais de 30 dias. Esse arquivo é **seu**: não compartilhe com ninguém.

---

## 4. Usando

- O Hunter fica no **ícone perto do relógio**. Ele checa os preços sozinho a cada 30 minutos.
- **Clique no ícone** para abrir o painel (`http://localhost/kurokami`).
- **A primeira checagem demora** (uns 10 a 40 minutos, conforme o tamanho da sua lista): ela importa o histórico de cada jogo e lê DLCs e bundles. Depois, cada checagem leva segundos.
- Na primeira vez ele **não** dispara uma enxurrada de avisos: registra o que já está em promoção e daí em diante avisa só as novidades.

### Abas do painel

- **Ofertas → Destaques** (clicar em *Ofertas* no topo abre aqui; teclas 1 a 4 trocam entre Ofertas, Biblioteca, Configurações e Carrinho, e Shift+1, 2 e 3 entre Destaques, Promoções e Lista; uma letra, Esc ou `/` abre uma barra no centro para buscar um jogo pelo nome na sua lista e em todas as promoções, sem os filtros, e Esc de novo fecha): no alto, um carrossel com as 10 melhores promoções da sua lista, com o **veredito** de cada uma (*Imperdível*: abaixo do menor preço dos últimos 2 anos por R$ 5 e 15% ou mais; *Menor preço*: no menor dos 2 anos, não fica mais barato; *Pode esperar*: o menor preço volta logo; *Preço de costume*) e duas frases: **quando deve vir a próxima promoção** (e por quanto) e **se esse preço costuma voltar** em 3 meses, medidas no histórico. Embaixo, **Hoje** em quatro colunas: Melhores ofertas e Menores históricos (fora da sua lista), **Bons e baratos** (bem avaliados até R$ 10, 25 ou 50) e a sua Lista de desejos; e as que **acabam em até 3 dias**. Tudo com o filtro do Destaques: só jogos, -50% ou mais, 500+ análises, sem os que você tem.
- **Ofertas → Promoções:** cartões de recortes no topo (Todas, Imperdíveis, Menores históricos, Bons e baratos, Grandes por pouco, Acabam em 3 dias, Das suas séries); um clique troca a grade de capas, outro volta para Todas. **Filtros ▾** abre os filtros (desconto, análises, tipo, os que você tem, lista, preço, avaliação, etiquetas); cada filtro ligado vira uma pílula com ✕ (Backspace tira o último). Na capa: o desconto na cor do veredito, ♥ se está na sua lista, **+** para pôr no carrinho (os de fora da lista passam a ser monitorados) e a barra do preço cheio até o menor em 2 anos.
- **Ofertas → Lista de desejos:** no topo, o **orçamento**: *com R$ 50 · 100 · 200 · 500 você leva N jogos por R$ X*, a combinação dos melhores negócios que cabe no valor e rende a maior economia, com "Pôr os N no carrinho". Depois os recortes (Compre agora, Acabam em 3 dias, Pode esperar, Vem aí, Até R$ 25), as abas Todos · Em promoção · Fora de promoção · Em breve e a visão por **franquias** (tecla T).
- **Tabela com todos os filtros** (no menu Ofertas, a antiga aba Promoções): os jogos da sua lista e todas as promoções da Steam (atualizadas a cada hora e no *Verificar agora*; o + põe no carrinho e monitora; os recordes chegam pela IsThereAnyDeal e, ao abrir a ficha de um jogo de fora da lista, o histórico das suas lojas vem na hora), num explorador como o da SteamDB. Filtros que se combinam: sua relação com o jogo (✓ só esses, ✕ esconder: na lista, monitorado, no carrinho, silenciado, tenho...), Conteúdo adulto (+18: oculto por padrão; *Mostrar* ou *Só +18*, pela classificação da Steam; jogos da sua lista nunca são ocultados), Mostrar só (os 4 tipos de preço), Tipo, Outros, preço, análises, nota, desconto e lançamento. Cada filtro ativo vira um chip com ×. A tabela ordena clicando no título da coluna (Shift+clique soma critérios) e tem a coluna **Costuma voltar** ("todo mês", "a cada ~3 meses", "1 vez por ano", "nunca teve esse desconto"...), que só informa: quanto mais raro, mais quente a cor (vermelho quando nunca teve, apagado quando é todo mês). A linha do Selo Kurokami ganha fundo e barra vermelha; o desconto vai do cinza (até -49%) ao vermelho cheio (-90% ou mais). Promoções abre sempre com "Desconto ≥ 50%", "Análises ≥ 500", "✕ Tenho" e só jogos (DLC em Tipo); Lista de desejos com os mesmos três filtros mais "✓ Na lista de desejos". "Restaurar padrão" volta aos de Promoções. No celular, os filtros ficam no botão **Filtros**. Clique num jogo para abrir a **ficha** (a mesma em todas as abas, como a do PlayStation): capa, logo, descrição, cinco números (preço, quando termina, análises, tempo para zerar pelo HowLongToBeat, nota da crítica; nos seus jogos, tempo jogado e conquistas), a fileira dos jogos da mesma franquia (os que faltam em preto e branco; dá para trocar a franquia à mão), o histórico em gráfico, o preço por loja, as formas de comprar, quando a promoção termina e as DLCs. Se só a Steam tiver o recorde, a ficha avisa ("Na Steam, é o menor preço já registrado. Nas suas lojas, Nuuvem já teve R$ 4,74 (07/2025).").
- As **análises da Steam** aparecem como informação, mas não decidem avisos: o jogo já está na sua lista de desejos.
- **Ficha do jogo** (clique em qualquer jogo): capa, descrição, cinco números e os botões; embaixo, caixas que abrem uma parte por vez, sem rolar a página: **1 Vale a pena?**, **2 Histórico de preços**, **3 Preço em todas as lojas**, **4 Franquia** e **5 Sobre o jogo** (clique ou aperte Shift+número; ‹ › ou as setas passam para o próximo jogo, Esc fecha). O histórico abre com o preço da Steam; a tecla T, os botões ou arrastar o gráfico para o lado mostram o menor preço entre todas as lojas.
- **Biblioteca ▾ → Biblioteca:** a **Coleção**, uma vitrine de capas com uma pilha por franquia ("N de M", a barra de progresso, as horas jogadas e quantos faltam), ou as **Franquias** em prateleiras que se arrastam para o lado (Shift+T alterna). Ordem em um clique (mais jogadas, recentes, A–Z, mais completas, maiores), índice A–Z à direita, `/` busca e as setas andam pelas capas. Clique numa franquia para abrir a **ficha da franquia** em tela cheia: os jogos em ordem de lançamento (os que faltam em preto e branco, com o preço), quanto você jogou, o que falta (com a loja do preço e + para o carrinho) e o **HowLongToBeat** (quantas horas de história faltam para zerar os que você tem, do mais curto ao mais longo); ‹ › passam para a próxima.
- **Biblioteca ▾ → Completar:** abre em **Texto**, com as franquias que têm jogo faltando (o que falta primeiro, com o preço de hoje); em **Capas**, os seus jogos com DLC faltando, com as que estão em promoção primeiro; clique para ver as DLCs por tipo e pôr todas, ou só as em promoção, no carrinho. *DLCs dos meus jogos em promoção ↗* no menu abre aqui.
- **Carrinho (só da Steam):** jogo cujo melhor preço está em outra loja não entra nele: no lugar do **+** aparece o **↗**, que abre a página do jogo naquela loja. Nos itens (jogos e bundles), escolha se entra **para a sua conta**, **de presente** ou **privado**. *Finalizar pedido* abre o carrinho da Steam. Para adicionar jogos, use **Adicionar jogo**, ao lado do resumo do pedido (nome, appid ou link da Steam): **um clique** no resultado já põe o jogo no carrinho (e passa a monitorá-lo), e a lista continua aberta para adicionar mais (Esc fecha). *Finalizar pedido* respeita a escolha e não repete o que já está no carrinho da Steam.
- **Configurações ▾ → Notificações:** os avisos que o Hunter mandou, por dia (Hoje, Ontem...), com o tipo (Selo Kurokami, Novo recorde, Keyshop...), o motivo, o preço avisado e o **preço de agora** (ainda nesse preço, mais barato, a promoção acabou). O mesmo jogo aparece uma vez, com os avisos anteriores contados; filtre por **Lojas oficiais** ou **Keyshops**.
- **Configurações:** em seções, com um menu do lado (Avisos, Lojas, Notificações, Frequência, Steam inteira, Keyshops, DLCs, Celular e outros PCs); ao mudar algo aparece embaixo a barra **Salvar**. Tem lojas, **Avisos** (Selo Kurokami ligado; Novo recorde, Igual ao recorde e Menor em 2 anos você liga se quiser, cada um com quantos avisos costuma dar por semana), desconto mínimo, keyshops, tipos de DLC, notificações e acesso pelo celular. Ligar um tipo não enche a tela de avisos: chega um resumo e, daí em diante, só os próximos.

### Avisos no Telegram (opcional, gratuito)
Para receber os avisos no celular, mesmo fora de casa: no Telegram, abra o **@BotFather**, envie `/newbot`, escolha um nome e guarde o **token** que ele devolve. No Hunter, vá em **Configurações → Telegram** (no menu do lado), cole o token e clique em **Conectar**. Depois abra o seu bot no Telegram, toque em **Iniciar** e clique em **Vincular conversa** no Hunter. Chega uma mensagem de confirmação. O token fica no Gerenciador de Credenciais do Windows, nunca num arquivo. Os avisos de oferta, "termina em breve" e os resumos passam a chegar nos dois lugares (para usar só o Telegram, desligue "Notificar no Windows"). O horário de silêncio vale para os dois.

### Pelo celular

Em **Configurações → Acesso pelo celular**, ligue a opção. Aparece um endereço (ex.: `http://192.168.0.10/kurokami`), um QR code e um **PIN**. No celular, no mesmo Wi-Fi, abra o endereço e digite o PIN uma vez. Se o Windows perguntar sobre o firewall, permita em **Redes privadas**.

---

## 5. Problemas comuns

| Problema | O que fazer |
|---|---|
| A notificação não aparece | *Configurações do Windows → Sistema → Notificações*: deixe ativado e desligue o *Não incomodar*. |
| "Lista de desejos vazia" | Deixe *Detalhes dos jogos* como **Público** na privacidade da Steam. |
| Chave recusada | Copie de novo; na IsThereAnyDeal use o campo **API Key**. |
| O painel não abre | Clique com o direito no ícone → **Reiniciar**. Se não houver ícone, abra o *Kurokami Hunter* pelo menu Iniciar. |
| Quero ver o que aconteceu | Ícone → **Ver log**. |

## 6. Atualizar

O Hunter procura versão nova **sempre que abre** e uma vez por dia enquanto fica aberto. Quando tem, chega uma notificação e aparece uma faixa vermelha no painel com **Atualizar agora**: ele baixa, instala por cima e abre de novo sozinho. Seus dados e chaves ficam.

Se preferir na mão: menu Iniciar → **Kurokami Hunter (Atualizar)**, ou ícone → **Procurar atualização…**

## 7. Desinstalar

*Configurações do Windows → Aplicativos → Aplicativos instalados → Kurokami Hunter → Desinstalar*. Os seus dados ficam em `%LOCALAPPDATA%\Kurokami Radar`; apague essa pasta se quiser remover tudo. As chaves ficam em *Gerenciador de Credenciais → Credenciais do Windows → Kurokami Radar* (nome antigo, mantido para não perder as chaves).

---

Detalhes técnicos (rodar pelo código, gerar o instalador, `config.json`): veja [TECNICO.md](TECNICO.md).
Preços via [IsThereAnyDeal](https://isthereanydeal.com), [GG.deals](https://gg.deals) e Steam.
