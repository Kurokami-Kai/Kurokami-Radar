# Spec 06 — Login Steam por QR (opcional)

Status: **Etapa 1 a fazer** · Pedido do dono em 04/10/2026 · Skills: `kurokami-code`, `coleta-e-apis`

**Duas etapas. Faça a Etapa 1 (teste), entregue o relatório e PARE. A Etapa 2 é escrita depois, com base no teste.**

## Problema
- **Hoje o Radar nunca entra na conta Steam** (`docs/decisoes.md`: "o Radar nunca recebe cookies da Steam"). Isso traz quatro limites:
  1. **Carrinho:** só funciona pela ponte do Tampermonkey, que muita gente não tem ou não sabe instalar.
  2. **Lista de desejos:** `GetWishlist` sem chave exige perfil com "Detalhes dos jogos" público.
  3. **Seguidos e ignorados:** dependem do `userdata.json`, que não existe no PC do dono (Etapa 1.3 da spec 04). Hoje ficam desativados.
  4. **Família Steam:** o Radar não sabe quais jogos a família já tem.
- **Prioridade do dono:** 1) carrinho sem Tampermonkey; 2) lista de desejos com perfil privado; 3) seguidos e ignorados; 4) jogos da família.

## Decisões do dono (04/10)
- **O login é opcional.** Sem login, tudo continua como hoje: perfil público, `userdata.json` e ponte do Tampermonkey. Nada pode quebrar para quem não entrar.
- **Login por QR** (o mesmo fluxo de "entrar com o app da Steam"). O Radar nunca vê nem guarda a senha.
- **Guardar a sessão.** O refresh token fica no Gerenciador de Credenciais do Windows, via `radar/credenciais.py` (o mesmo cofre das chaves da ITAD e da GG.deals). O access token fica só em memória.
- **Botão "Sair da Steam":** revoga o token na Steam (se houver endpoint para isso) e apaga do cofre.
- **Isso muda uma decisão de segurança.** Registre em `docs/decisoes.md` só na Etapa 2.

## Regras de segurança (valem para as duas etapas)
1. **Token nenhum em arquivo, log, banco, config, `dados/`, relatório ou Git.** Nos logs e no relatório, mostre no máximo os 6 primeiros caracteres seguidos de "…".
2. **Rede:** só HTTPS para `api.steampowered.com`, `login.steampowered.com` e `store.steampowered.com`, com `rede.py` (ritmo e backoff).
3. **Só a própria conta** do usuário logado. Ritmo baixo: no máximo 1 chamada por segundo nos testes.
4. **Toda ação que muda a conta** (carrinho, lista de desejos) tem 3 passos:
   - fotografar o estado antes;
   - fazer a ação;
   - desfazer e conferir que o estado ficou igual ao de antes.

   Se não conseguir desfazer, pare e avise no relatório o que ficou diferente.
5. **Endpoints:** confirme cada um na documentação pública antes de usar (protobufs do SteamDatabase/SteamTracking e steamapi.xpaw.me). Os nomes abaixo são **candidatos**: se um não existir ou não aceitar o token, registre isso e siga para o próximo.

## Etapa 1 — teste (o app não muda)
- **Onde:** script novo `tools/teste_login_steam.py`. Nada em `radar/` muda e não há versão nova.
- **Dependências:** se faltar alguma (ex.: `qrcode`), instale num venv do scratchpad, como foi feito com o Playwright. Nada no Python do sistema.
- **O que vai para o Git:** só o script. Resultados brutos (sem tokens) vão para `dados/sonda/login_steam.json`.

### 1. Login por QR
- **Fluxo candidato:** `IAuthenticationService/BeginAuthSessionViaQR` → mostrar o QR → `PollAuthSessionStatus` até aprovar → refresh token e access token.
- **Como mostrar o QR:** salve como PNG em `dados/sonda/qr.png`, abra com `os.startfile` e espere até 3 minutos.
- **Tipo de plataforma:** teste com o tipo de navegador web, que é o necessário para a loja aceitar a sessão. Diga qual valor funcionou.
- **No relatório:**
  - nome do perfil e SteamID (só os 4 últimos dígitos);
  - validade do access token e do refresh token (campo `exp` do JWT, sem verificar a assinatura; só as datas);
  - se a renovação (`GenerateAccessTokenForApp` ou equivalente) funciona e por quanto tempo vale o token novo.
- **Celular:** teste se abrir o link do desafio no próprio celular (em vez de escanear) também aprova. Isso decide se dá para entrar pelo painel aberto no celular.

### 2. Carrinho (prioridade 1)
- **Leitura:** leia o carrinho da conta (candidato: `IAccountCartService/GetCart`). Liste quantos itens há e os nomes.
- **Escrita:** com o carrinho fotografado:
  - adicione 1 item (candidato: `AddItemsToCart`) usando o `packageid` de um jogo do `dados/carrinho.json` do Radar (ou, se estiver vazio, de um jogo barato da lista);
  - confira que apareceu;
  - remova (candidato: `RemoveItemFromCart`);
  - confira que o carrinho voltou a ser igual ao da foto.
- **Repita com 1 bundle**, se a API aceitar bundle.
- **Também medir:**
  - se a aba do carrinho na loja Steam (navegador) mostra a mudança na hora;
  - se precisa de verificação de idade;
  - quanto tempo leva cada chamada;
  - quantos itens dá para mandar de uma vez.

### 3. Lista de desejos (prioridade 2)
- **Leitura:** leia com o token (candidato: `IWishlistService/GetWishlist` com o access token). Compare com a leitura pública de hoje: mesmo número de itens e mesma ordem de prioridade.
- **Perfil privado:** se der para testar sem mudar a privacidade do perfil, diga como; se não der, deixe registrado que a confirmação fica para a Etapa 2.
- **Escrita:** adicione 1 jogo que NÃO está na lista (um gratuito qualquer), confira, remova e confira que voltou ao estado de antes. Candidatos: `IWishlistService/AddToWishlist` e `RemoveFromWishlist`.

### 4. Seguidos e ignorados (prioridade 3)
- **Seguidos:** candidato `IStoreService/GetGamesFollowed`, ou equivalente.
- **Ignorados:** o `userdata` da loja (`/dynamicstore/userdata/` com a sessão web, ou um endpoint da API que dê o mesmo).
- **No relatório:** quantos seguidos e quantos ignorados, e quantos de cada estão na lista de desejos.

### 5. Família Steam (prioridade 4)
- **Candidatos:** `IFamilyGroupsService/GetFamilyGroupForUser` e `GetSharedLibraryApps`.
- **No relatório:** se o dono tem família; número de membros (sem nomes); quantos jogos compartilhados; quantos jogos da lista de desejos já estão na biblioteca da família.

### 6. Sair
- Revogue a sessão (candidato: `IAuthenticationService/RevokeRefreshToken`) e confirme que a renovação passa a falhar.
- Diga se a sessão some de "Dispositivos autorizados" na conta Steam.

### Entrega da Etapa 1
- **Uma tabela:** item | funciona? | endpoint e parâmetros que funcionaram | tempo por chamada | limites ou erros vistos.
- **Recomendações para a Etapa 2:**
  - o que a ponte do Tampermonkey ainda faria e o que dá para tirar;
  - como o QR apareceria no painel;
  - como renovar o token sozinho.
- **Por fim:** confirme que nenhum token foi gravado em disco (procure em `dados/` e no log) e que a conta ficou igual ao estado de antes do teste.
- Anote em `docs/aprendizados.md` (até 5 linhas) o gasto de `/usage` da tarefa e onde foi maior.
- **PARE.**

## Etapa 2 — a escrever depois do teste
Itens previstos, para orientar o teste (números e detalhes saem da Etapa 1):
- **Configurações:** bloco "Conta Steam" com "Entrar com QR" (o QR aparece no painel), "Conectado como <nome>" e "Sair da Steam".
- **Carrinho direto pela conta,** com a ponte do Tampermonkey continuando como alternativa para quem não entrar.
- **Lista de desejos pela conta,** inclusive com perfil privado.
- **Seguidos e ignorados:** passam a vir de `conta_steam.relacao`. É a única função que muda, como foi preparado na spec 04.
- **Família:** uma linha nova "Na família" na relação com o jogo da aba Promoções. Se os jogos da família contam como "tenho" para os avisos fica para decidir com os números do item 5.
