# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

## 2026-10-09 — spec 09 Etapa 2: três amostras da Biblioteca
- **Amostra com dados pessoais vai para `dados/`** (ignorada pelo Git): script no scratchpad chama `painel.api_biblioteca` + `series.franquias` numa cópia do banco e injeta o JSON no modelo HTML.
- **Ordem padrão antes de ordenar:** `tool()` fixava a ordem depois do `sort` e a 1ª pintura saiu sem ordem; testar cada tela num laço JS (opção × página × modo) achou isso mais rápido que prints.
- **Prints do navegador do app falham depois de `resize_window`** (a pane muda de largura e limpa a emulação): confira pelo DOM (`getBoundingClientRect`, contagens) em vez de insistir.
- **DLCs possuídas = 0 sem `userdata.json`:** antes de concluir "bug no Completar", `grep userdata radar.log`.
- **Cinco rodadas de amostras com dados reais fecharam a Biblioteca (H2):** o dono decide melhor vendo; o que travou cada rodada foi detalhe visual medido (altura da ficha em 1280×900, capas centralizadas, barra que não lê 100%). Referência para outro chat vai para `docs/specs/` com dados reduzidos e tempos sintéticos; a completa fica em `dados/`.
- **Regra de dado sintético com `appid % 5`** zerou uma franquia inteira (os appids do GTA são múltiplos de 10): use um hash, não um módulo pequeno.
- **O navegador do app não abre arquivo local acima de ~512 KB** ("couldn't open file"): 510 KB abriu, 513 não. Tire dos dados o que a amostra não usa.
- **`Set-Content -Encoding utf8` no PowerShell 5.1 grava BOM** (apareceu na mensagem do commit): escreva o texto com a ferramenta Write.
- **Mensagem de commit com aspas no PowerShell 5.1 quebra** (vira pathspec): use `git commit -F arquivo.txt` do scratchpad.
- **Aba do navegador do app recusa JS em arquivo local às vezes** ("shows a local file"): `preview_start` com a mesma URL abre outra aba que aceita.
- **Amostra com dados reais pegou um bug de produção** (franquia "45527500"): contar no banco os campos com parte numérica respondeu em 1 consulta. `zoom` na região do print funciona quando o `screenshot` cheio sai em escala estranha.

## 2026-10-08 (madrugada do 09) — v0.16.0 publicada; spec 09 Etapa 1 (ficha B+)
- **Medir a fonte no banco antes da regra:** contar as `franquia` da Steam por nº de nomes distintos mostrou na hora as editoras (WB Games, Team17 Digital...); a regra "nomes muito diferentes" da spec não separava (Sonic tem 8 nomes em 10 jogos).
- **Heredoc quebrou aspas pela 4ª vez** (script de docs): para textos com aspas, sempre Write num `.py` do scratchpad.
- **Print do navegador do app atrasa a pintura das imagens** (capas pretas, seta "sumida"): confira pelo DOM (`naturalWidth`, `getComputedStyle`) antes de "corrigir".
- **Revisor pegou 4 erros reais** (corrida entre fichas, prefixo "Team" apagando Team Fortress, tempo jogado derrubando a biblioteca, conexão sem `finally`). Vale rodá-lo em paralelo com a escrita dos docs.
- **Augmented Steam às vezes leva 15–20 s sem cache:** a ficha abre antes e redesenha quando o extra chega.

## 2026-10-08 (fim da noite) — filtro Monitorado, seguidos/ignorados pela extensão
- **"Until Then aparece" de novo era o banco com `possuido=1` em 0 jogos** (os 401 de 07–08/10 zeraram antes da correção). Testar a chave pelo próprio `steam.biblioteca_api` (script no scratchpad, sem imprimir a chave) respondeu em 1 chamada.
- **Formato da Steam sem login dá para conferir no navegador do app:** `#application_config` tem `data-userinfo` (`logged_in`, país) e `/dynamicstore/userdata/` devolve as chaves `rg*` vazias. O `steamid` logado não deu para ver.
- **Amostras de layout em HTML com dados reais + navegador do app:** o arquivo abre como cópia estática (`data:`), então recarregar não pega a edição: navegue de novo (abre outra aba; pegue o `tabId` em `tabs_context`) e use `resize_window` 1280×1000 com a pane escondida para print nítido.
- **Rota nova testada chamando a função direto** numa cópia do banco (`caminhos.RAIZ_DADOS/ARQ_BANCO` trocados no script): mais barato que subir o `painel_copia.py`.

## 2026-10-08 (madrugada) — Ofertas, +18, ficha da Steam inteira, biblioteca com 401
- **"Jogo que eu tenho aparece" era a biblioteca vazia, não filtro:** o log mostrou `HTTP Error 401` desde 07/10 20:31 e `biblioteca: 0 itens`. Antes de mexer em filtro, `grep "biblioteca:" radar.log`.
- **A Query da Steam já devolve `content_descriptorids`** sem pedir nada no `data_request` (3 e 4 = sexual): medir com 1 chamada antes de planejar etapa extra.
- **`painel_copia.py` morto à força deixa a cópia do banco no %TEMP%** (`kr-painel-*`, havia 16): apague depois do teste. A rota é `/api/...` na raiz, não `/kurokami/api`.
- **Subagente explorador para o mapa das abas + revisor no fim** pegou 2 erros reais (faixa afirmando "chave recusada" para qualquer erro; 500 com banco ocupado).

## 2026-10-08 (noite) — recordes da Steam inteira, menus no topo
- **Antes de perseguir uma contagem da SteamDB, confira 3 itens na loja** (`appdetails`): os 40 mil dela eram promoções já acabadas (fila de atualização cheia, o aviso amarelo dela diz).
- **A ITAD tem cota (~100 chamadas em 5 min)** e as minhas sondagens seguidas gastaram a cota do teste seguinte (429 com `Retry-After` 210 s): espaçar sondagens e, no código, parar no primeiro 429 em vez de esperar dentro do laço.
- **Arquivo .py de edição no scratchpad + `assert count == 1`** funcionou sem retrabalho (o único heredoc tentado quebrou de novo nas aspas).
- **O navegador do app guardou o `painel.html` velho:** depois de editar, navegue com `?v=N` para forçar a página nova.

## 2026-10-08 — spec 07, Steam inteira
- **Os 126 MB/dia da spec 04 eram falta de gzip:** a Steam comprime se pedir (1,5 MB → 150 KB por página). Meça o tamanho com `Accept-Encoding: gzip` antes de concluir que algo é pesado.
- **`cmp_to_key` com 100 mil linhas leva segundos;** ordenações estáveis do último critério ao primeiro (nulos separados) dão o mesmo resultado em ~100 ms.
- **Teste de desempenho barato:** cópia do banco + 100 mil linhas sintéticas em `steam_promo` + `painel.api_promocoes` chamado direto (sem servidor).
- **Reescrever histórico (e-mail pessoal, 08/10):** `git filter-branch --env-filter ... --tag-name-filter cat -- --all` (o filter-repo não está instalado), backup com `git bundle` antes, e as 4 tags num push só: com mais de 3 tags por push o GitHub não dispara o workflow de instalador.
- **O hook que mostra o `painel.html` no navegador do app troca a aba ativa:** depois de editar o HTML, navegue de novo para a porta da cópia (a aba nova vem com outro `tabId`).

## 2026-10-08 — QR trocado pela extensão do Radar
- **Heredoc de novo quebrou aspas** num script de edição: edite o `.py` do scratchpad com a ferramenta Edit em vez de remendar via Bash.
- **`troca` com texto que aparece duas vezes** (`await carregarContaQR();` estava no topo e no Finalizar): inclua a linha de cima no trecho para ele ficar único.
- **A estrutura da página da Steam dá para conferir sem login** no navegador do app (`#application_config` → `store_user_config.webapi_token` vazio). Já adicionar ao carrinho pela extensão só o dono testa, com a conta dele.

## Antigas, resumidas (até 07/10)
- **Scripts de edição:** Write num `.py` do scratchpad (heredoc quebra aspas, crases e `\`), `assert s.count(a) == 1` antes de cada troca, trecho único (inclua a linha de cima) e corte só entre marcadores nomeados, com `git diff --stat` logo depois.
- **Testes:** `painel_copia.py` velho pode seguir vivo em outra porta (use `--porta 8801`); `tools/rodar_instalado.py` para o caminho real (achou o que os sintéticos não acharam); teste que mexe na conta guarda o conteúdo a cada passo; `GetCart` só lê. Medir na fonte (`Query` precisa de `sort: 2`).
- **Leitura:** mapeie com `tools/mapa.py` e leia só a função; código morto por script de referências, procurando também em `tools/`. Releia a skill antes do último passo; `gh` não existe: workflow pela API pública.
- **Economia de tokens (04/10):** `.claude/settings.json` (`opusplan`), subagentes `explorador` (Haiku) e `revisor` (Sonnet), skill `economia-de-contexto`. Agente novo só carrega em sessão nova. `ccusage` pelo PowerShell; o hook do rtk o dono roda.
