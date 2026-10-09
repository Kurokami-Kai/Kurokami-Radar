# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

## 2026-10-09 — spec 09: Ofertas, da O1/O2 à quarta rodada (previsão medida)
- **Medir antes de propor a métrica:** a nota feita à mão parecia razoável, mas o backtest mostrou que quase todo preço volta (96% em 12 meses) e que "costuma voltar" quase não separa; o que separa é a 1ª vez nesse preço. O "último preço", chamado de covarde, é o melhor previsor (67%): a resposta foi mostrar a confiança medida.
- **Revisor no backtest pegou 4 erros reais:** "6 de 6" misturando jogos com 2–3 promoções, comparação usando a data futura, grade do ajuste batendo no limite (mudou a conclusão: a Gama-Poisson empata) e grupos de 15–27 casos virando regra. Rode o revisor antes de escrever os números nos docs.
- **Não rodar coleta pelo Radar do dono para encher amostra** (puxei 14 min de ITAD sem pedir; ele cortou). Amostra = API de listagem + banco em modo leitura. O Radar em `localhost` é o instalado (banco em `%LOCALAPPDATA%`), não o `dados/` do código.
- **Amostras servidas por `http.server` só de `dados/amostras`** (launch.json "amostras"); arquivo local não abre no navegador do app e servir `dados/` inteiro expõe o banco.
- **Prints do navegador do app seguem instáveis:** medir pelo DOM num laço (página × filtro), `resize_window` 1440×900 logo antes do print; capas pretas = `loading=lazy` ainda carregando.

## 2026-10-09 — spec 09 Etapa 2: amostras da Biblioteca (resumo)
- Amostra com dados pessoais vai para `dados/` (fora do Git); medir pelo DOM num laço (opção × página × modo) em vez de prints; arquivo local acima de ~512 KB não abre no navegador do app; `Set-Content` grava BOM e aspas quebram o commit no PowerShell 5.1 (use `git commit -F`); hash, não `appid % 5`, para dado sintético; cinco rodadas com dados reais fecharam a H2.

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

## Antigas, resumidas (até 08/10)
- **Steam inteira e extensão (08/10):** peça gzip antes de achar algo pesado (1,5 MB → 150 KB); ordenar estável do último critério ao primeiro em vez de `cmp_to_key`; teste de desempenho com cópia do banco + linhas sintéticas chamando `painel.api_promocoes` direto; reescrever histórico com `git filter-branch` e `git bundle` de backup; a página da Steam dá para conferir sem login no navegador do app.
- **Scripts de edição:** Write num `.py` do scratchpad (heredoc quebra aspas, crases e `\`), `assert s.count(a) == 1` antes de cada troca, trecho único (inclua a linha de cima) e corte só entre marcadores nomeados, com `git diff --stat` logo depois.
- **Testes:** `painel_copia.py` velho pode seguir vivo em outra porta (use `--porta 8801`); `tools/rodar_instalado.py` para o caminho real (achou o que os sintéticos não acharam); teste que mexe na conta guarda o conteúdo a cada passo; `GetCart` só lê. Medir na fonte (`Query` precisa de `sort: 2`).
- **Leitura:** mapeie com `tools/mapa.py` e leia só a função; código morto por script de referências, procurando também em `tools/`. Releia a skill antes do último passo; `gh` não existe: workflow pela API pública.
- **Economia de tokens (04/10):** `.claude/settings.json` (`opusplan`), subagentes `explorador` (Haiku) e `revisor` (Sonnet), skill `economia-de-contexto`. Agente novo só carrega em sessão nova. `ccusage` pelo PowerShell; o hook do rtk o dono roda.
