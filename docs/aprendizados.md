# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

## 2026-10-09 — histórico em uma linha + faixa; "antes desta promoção" coerente
- **"Contraditório" eram duas definições de "esta promoção":** `analise` corta no preço de agora, `previsao` na onda de episódios (folga de 1 dia entre lojas). Imprimir os `segs`/`eps` do jogo do print (script no scratchpad lendo o banco) achou em 1 rodada; depois contar quantos mudam (19/218).
- **Episódio dividido precisa de `<=` no "passado"** (`e[1] <= atual[0]`): com `<` a parte de antes sumia e nada mudava.
- **Faixa por loja contra o maior preço da própria loja** pinta lojas regionais de -90% o ano todo: mostrar só as que alertam por padrão.

## 2026-10-09 — abas da ficha, lojas em tabela, notas alinhadas
- **"Fica fixado bugado" era o foco:** clicar na aba 1 e apertar 2 deixava o contorno de `:focus-visible` na 1 (o teclado liga o anel). Passar o foco para a aba escolhida e tirar o contorno dela resolveu.
- **Tabela larga em duas colunas estoura** no painel de ~1100 px: lojas na largura toda e as formas de comprar embaixo.
- **`fxAba` antes de `abrirJogo` terminar não vale:** para testar um painel, ponha `MABA` e depois abra a ficha.

## 2026-10-09 — ficha em painéis, colunas alinhadas, fundo vivo
- **"Desalinhado" era coluna `auto`:** o -90% andava porque a largura do preço (e da etiqueta GMG) variava por linha; caixas de largura fixa (grid 50px + 80px, loja embaixo do preço) e o calor sem negrito resolveram.
- **Flex column na `.mbox` não alcança os netos:** o painel não crescia porque o filho direto é `#mbody`; ele também precisa ser flex (medir `getBoundingClientRect` mostrou na hora).
- **Porta 8801 ocupada de novo:** entrada temporária 8803 no `launch.json` e `git checkout` dele antes do commit.

## 2026-10-09 — carrinho por loja, HLTB na franquia, Completar em Texto
- **Uma causa do "achei que era Steam" era empate:** o FF XIV tinha R$ 52,99 na Steam e na GMG, e `min(..., key=preco)` ficava com a primeira linha do banco (GMG). Ao mostrar "a loja do melhor preço", desempate pela Steam.
- **`${}` dentro de aspas simples não interpola:** trocar `title="Pôr no carrinho"` por `${maisT(o)}` em massa pegou 4 trechos que eram `'...'` e não template; procure no DOM por `title` com `${` depois de uma troca dessas.
- **`window.open` com `noopener` sempre devolve `null`** (não dá para saber se bloqueou) e o Chrome só libera uma aba por clique: abra sem `noopener`, zere `opener` e liste os links que vieram `null`.
- **Teste do Finalizar sem abrir nada:** trocar `window.open` por um registro no console do painel (e marcar `data-kurokami-ext`) mostrou o endereço da Steam e as abas das outras lojas sem sair do app.
- **Porta 8801 ocupada por cópia velha de outra conversa:** entrada temporária no `launch.json` (8803) e `git checkout` dele no fim.

## 2026-10-09 — paleta por papel e escala de calor
- **`git checkout` de um arquivo trouxe CRLF** e o script de troca (multilinha, com LF) parou de achar o trecho: normalize `\r\n` ao ler e devolva ao gravar.
- **MutationObserver registrado no fim do script não vê o primeiro desenho** (Ofertas renderiza na carga): chame a função uma vez logo depois de `observe`.
- **"Tudo vermelho" era o problema, não a cor:** o mesmo `#ff4655` fazia link, nota, desconto, etiqueta e botão. Separar por papel (comprar / ativo / clicável / calor) e tirar o vermelho do que não é oferta (notas, botões secundários, linha de baixo das colunas) resolveu mais que trocar tons.

## 2026-10-09 — aba Notificações nova; extensão recusada pela loja do Edge
- **A loja do Edge recusa `description` acima de 132 caracteres** no `manifest.json`: o `checar.py` confere agora (e pegou a 1ª versão encurtada, com 134).
- **`ref_N` do `find` vence ao navegar:** um clique com ref velho caiu no Carrinho; depois de navegar, rode `find` de novo ou clique por `javascript_tool`.

## 2026-10-09 — azul e verde viram vermelho
- **Mapa de hex com alfa preservado nos 3 arquivos (painel, ofertas, biblioteca) + varredura do DOM por matiz** (abas e iframe) achou as 2 sobras (ícone da lista, "igual ao recorde") que o mapa não cobria; troca de texto de comentário que contém hex tem de vir depois do mapa (o assert pegou).
- **Verde com sentido fica** (exigir × excluir, feito, turquesa dos vereditos): trocar tudo por vermelho apagaria a diferença entre bom e ruim.

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

## 2026-10-09 — spec 09 Etapa 2: amostras da Biblioteca (resumo)
- Amostra com dados pessoais vai para `dados/` (fora do Git); medir pelo DOM num laço (opção × página × modo) em vez de prints; arquivo local acima de ~512 KB não abre no navegador do app; `Set-Content` grava BOM e aspas quebram o commit no PowerShell 5.1 (use `git commit -F`); hash, não `appid % 5`, para dado sintético; cinco rodadas com dados reais fecharam a H2.

## Antigas, resumidas (até 08/10)
- **v0.16.0 e ficha B+ (08–09/10):** medir a fonte no banco antes da regra (franquias da Steam por nº de nomes mostrou as editoras); heredoc quebra aspas (Write num `.py`); print do navegador atrasa imagens (conferir pelo DOM); revisor em paralelo com os docs pegou 4 erros reais; Augmented Steam leva 15–20 s sem cache (a ficha abre antes e redesenha); "jogo que tenho aparece" era `possuido=1` zerado (testar a chave pelo `steam.biblioteca_api`); formato da Steam sem login se confere no navegador do app; rota nova se testa chamando a função numa cópia do banco.
- **Ofertas, 5ª e 6ª rodadas (09/10):** conferir se a página usa os mesmos pontos de dados do backtest antes de chamar a previsão de "medida"; ouvir a intuição do dono e medir (novo patamar: 10% mínimo, mediana das 3, grupo de controle); critério em reais além de %; `.full` com 100vw desalinha (barra de rolagem); pane escondida mede zero (`resize_window` antes); contar cada grupo antes de mostrar.
- **Ofertas, 7ª rodada (09/10):** scripts sempre pelo Write (`cat >` sem heredoc trava 2 min); porta 8802 pode ser de outra conversa; "bem avaliado" só pela % premia brinquedo de R$ 2 (pesar análises e preço cheio); contar o filtro antes de mostrar a coluna.
- **Ofertas O1 à 4ª rodada (09/10):** medir antes de propor métrica (backtest: o "último preço" prevê 67%); revisor no backtest pegou 4 erros reais; não rodar coleta pelo app do dono para encher amostra (amostra = API de listagem + banco em modo leitura); amostras só por `http.server` de `dados/amostras`; prints instáveis: medir pelo DOM.
- **Ofertas, +18, biblioteca com 401 (08/10, madrugada):** "jogo que tenho aparece" era a biblioteca vazia (`grep "biblioteca:" radar.log` antes de mexer em filtro); a Query já traz `content_descriptorids`; `painel_copia.py` morto deixa `kr-painel-*` no %TEMP% (apague); a rota é `/api/...` na raiz; explorador + revisor pegaram 2 erros reais.
- **Steam inteira, recordes e menus (08/10, noite):** confira 3 itens na loja antes de perseguir contagem da SteamDB; a ITAD tem cota (~100 chamadas em 5 min): espaçar sondagens e parar no primeiro 429; `.py` de edição no scratchpad com `assert count == 1`; navegue com `?v=N` para o navegador do app largar o `painel.html` velho.
- **Steam inteira e extensão (08/10):** peça gzip antes de achar algo pesado (1,5 MB → 150 KB); ordenar estável do último critério ao primeiro em vez de `cmp_to_key`; teste de desempenho com cópia do banco + linhas sintéticas chamando `painel.api_promocoes` direto; reescrever histórico com `git filter-branch` e `git bundle` de backup; a página da Steam dá para conferir sem login no navegador do app.
- **Scripts de edição:** Write num `.py` do scratchpad (heredoc quebra aspas, crases e `\`), `assert s.count(a) == 1` antes de cada troca, trecho único (inclua a linha de cima) e corte só entre marcadores nomeados, com `git diff --stat` logo depois.
- **Testes:** `painel_copia.py` velho pode seguir vivo em outra porta (use `--porta 8801`); `tools/rodar_instalado.py` para o caminho real (achou o que os sintéticos não acharam); teste que mexe na conta guarda o conteúdo a cada passo; `GetCart` só lê. Medir na fonte (`Query` precisa de `sort: 2`).
- **Leitura:** mapeie com `tools/mapa.py` e leia só a função; código morto por script de referências, procurando também em `tools/`. Releia a skill antes do último passo; `gh` não existe: workflow pela API pública.
- **Economia de tokens (04/10):** `.claude/settings.json` (`opusplan`), subagentes `explorador` (Haiku) e `revisor` (Sonnet), skill `economia-de-contexto`. Agente novo só carrega em sessão nova. `ccusage` pelo PowerShell; o hook do rtk o dono roda.
