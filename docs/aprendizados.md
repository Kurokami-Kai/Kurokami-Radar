# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

## 2026-10-09 — Ofertas (amostra 8) e Biblioteca (H2) no painel
- **Pedido "implemente as amostras" = os geradores fora do Git** (`dados/dados_ofertas4/6/7.py`, scratchpad antigo com `dados_bib.py`): achar a cadeia de dados antes de escrever deu o formato exato das linhas; o código das amostras entrou quase intacto num iframe (CSS e nomes delas brigariam com os do painel).
- **Limpar CSS morto por regra, não por linha** (regras de várias linhas, várias regras por linha) e procurar classe montada no JS (`pp-${t}`): a primeira passada apagou `pp-novo/24m` e a constante `TIPO_COR`, que o console pegou na hora. Depois de tirar código, compare os nomes declarados antes/depois e procure os que ainda são usados.
- **`cat > /dev/null` no fim de um comando travou de novo** (espera entrada): nunca terminar comando com `cat` sem arquivo.
- **"DLCs em promoção" pela tabela achava 5 de 129:** antes de trocar uma tela por um atalho, conte o resultado nas duas.

## 2026-10-09 — Kurokami Hunter: nome, paleta preta, logo, Configurações
- **Classe nova colidiu com uma antiga** (`.crow` já era a linha do carrinho e virou grid): o grep por `^\.crow` não achou porque a regra estava depois de `}` na mesma linha. Prefixe classes novas da aba (`cfg-…`) e liste as regras que casam pelo JS (`cssRules` + `matches`) quando o layout sair estranho.
- **Trocar paleta por mapa de hex** (40 tons, com alfa preservado) + varredura pelo DOM em todas as abas e na ficha (`getComputedStyle`, azul com pouca luz) achou zero sobras; mais barato que olhar print por print.
- **Renomear em massa protege identificadores:** a troca de "Radar" nos docs mudou o nome do keyring no README (as chaves continuam em `Kurokami Radar`); conferir com `git grep` cada nome que o código usa (pasta, keyring, tarefa, exe, instalador) depois da troca.
- **Script Python no scratchpad lendo em modo texto troca CRLF por LF** no `painel.html` (o Git normaliza, sem estrago); para docs com CRLF, grave com `newline` de CRLF.

## 2026-10-09 — spec 09: Ofertas, oitava rodada (ficha curta, recortes, orçamento)
- **"Os melhores que cabem" em ordem gulosa levou 2 jogos com R$ 100** (os imperdíveis caros entram primeiro): para orçamento, mochila pela economia (9 jogos). Conferir a saída com 4 valores antes de mostrar.
- **Encurtar texto expôs uma contradição** (duas datas diferentes para "volta"): ao resumir, escolha uma fonte só para cada pergunta.

## 2026-10-09 — spec 09: Ofertas, sexta rodada (piso e patamar)
- **A amostra e o backtest discordavam na definição:** o backtest chama de "último preço" a promoção que acabou de acabar; a amostra pulava a promoção de agora. Antes de dizer que a previsão é "a medida", confira se a página usa os mesmos pontos de dados do backtest.
- **Ouvir a intuição do dono e medir:** "novo patamar" virou uma pergunta de 20 linhas no backtest e mudou o texto da previsão. O revisor pegou queda de 1–2% contando como "preço novo" e a penúltima promoção como "patamar de antes": com 10% mínimo, mediana das 3 e grupo de controle, a conclusão ficou (62%), com outros números.
- **Critério em reais, não só em %:** "imperdível" sem ganho mínimo em R$ punha um jogo de R$ 4 no topo.
- **`.full` com 100vw desalinha da página** (a largura conta a barra de rolagem); meça as bordas pelo DOM depois de a animação de entrada terminar.

## 2026-10-09 — spec 09: Ofertas, quinta rodada (três modelos A/B/C)
- **Amostra nova sem o Radar aberto:** os dados da amostra anterior estão embutidos no HTML (`const D=`); extrair dali + banco em modo leitura evitou API e rede.
- **Pane escondida mede zero:** `innerWidth` 0 e `visibilityState` hidden deram larguras 0 e alturas absurdas; chame `resize_window` antes de medir e confira `innerWidth`. Com a pane escondida, `focus()` não dispara `focusin`: teste pelo caminho do código (`andar`), não pelo evento.
- **Conte cada grupo antes de mostrar:** "Vem aí" em 45 dias pegava 361 de 573 jogos (quase todo jogo entra em promoção todo mês); com "no menor preço, 4+ das 6" caiu para 52 e passou a dizer algo.

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

## Antigas, resumidas (até 08/10)
- **Ofertas, 7ª rodada (09/10):** scripts sempre pelo Write (`cat >` sem heredoc trava 2 min); porta 8802 pode ser de outra conversa; "bem avaliado" só pela % premia brinquedo de R$ 2 (pesar análises e preço cheio); contar o filtro antes de mostrar a coluna.
- **Ofertas O1 à 4ª rodada (09/10):** medir antes de propor métrica (backtest: o "último preço" prevê 67%); revisor no backtest pegou 4 erros reais; não rodar coleta pelo app do dono para encher amostra (amostra = API de listagem + banco em modo leitura); amostras só por `http.server` de `dados/amostras`; prints instáveis: medir pelo DOM.
- **Ofertas, +18, biblioteca com 401 (08/10, madrugada):** "jogo que tenho aparece" era a biblioteca vazia (`grep "biblioteca:" radar.log` antes de mexer em filtro); a Query já traz `content_descriptorids`; `painel_copia.py` morto deixa `kr-painel-*` no %TEMP% (apague); a rota é `/api/...` na raiz; explorador + revisor pegaram 2 erros reais.
- **Steam inteira, recordes e menus (08/10, noite):** confira 3 itens na loja antes de perseguir contagem da SteamDB; a ITAD tem cota (~100 chamadas em 5 min): espaçar sondagens e parar no primeiro 429; `.py` de edição no scratchpad com `assert count == 1`; navegue com `?v=N` para o navegador do app largar o `painel.html` velho.
- **Steam inteira e extensão (08/10):** peça gzip antes de achar algo pesado (1,5 MB → 150 KB); ordenar estável do último critério ao primeiro em vez de `cmp_to_key`; teste de desempenho com cópia do banco + linhas sintéticas chamando `painel.api_promocoes` direto; reescrever histórico com `git filter-branch` e `git bundle` de backup; a página da Steam dá para conferir sem login no navegador do app.
- **Scripts de edição:** Write num `.py` do scratchpad (heredoc quebra aspas, crases e `\`), `assert s.count(a) == 1` antes de cada troca, trecho único (inclua a linha de cima) e corte só entre marcadores nomeados, com `git diff --stat` logo depois.
- **Testes:** `painel_copia.py` velho pode seguir vivo em outra porta (use `--porta 8801`); `tools/rodar_instalado.py` para o caminho real (achou o que os sintéticos não acharam); teste que mexe na conta guarda o conteúdo a cada passo; `GetCart` só lê. Medir na fonte (`Query` precisa de `sort: 2`).
- **Leitura:** mapeie com `tools/mapa.py` e leia só a função; código morto por script de referências, procurando também em `tools/`. Releia a skill antes do último passo; `gh` não existe: workflow pela API pública.
- **Economia de tokens (04/10):** `.claude/settings.json` (`opusplan`), subagentes `explorador` (Haiku) e `revisor` (Sonnet), skill `economia-de-contexto`. Agente novo só carrega em sessão nova. `ccusage` pelo PowerShell; o hook do rtk o dono roda.
