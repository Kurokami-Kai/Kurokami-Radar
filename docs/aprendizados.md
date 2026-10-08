# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

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

## 2026-10-07 — busca do carrinho ao lado do resumo
- **O `painel_copia.py` velho na 8799 continuava vivo** e o modo automático não deixa encerrar processo de outra sessão: suba a cópia em outra porta (`--porta 8801`) em vez de tentar matar.

## 2026-10-07 — carrinho só Steam + modos (conta/presente/privado)
- **`painel_copia.py` esquecido numa sessão anterior continuava na porta 8799** e respondia com código velho (loja "Nuuvem", `modo` nulo): antes de testar, confira `netstat -ano | findstr :8799` e mate o antigo.
- **`GetCart` (só leitura) mostra o formato real** (`flags:{is_gift,is_private}`) sem mexer na conta; a escrita com `flags` no `AddItemsToCart` **não foi testada na conta real** (a conferência de volta avisa em `modo_diferente`).

## 2026-10-07 — spec 06, Etapa 1 (teste do login Steam)
- **Gasto:** ~92 mil tokens de contexto ao fim (Sonnet 5.5, 9% da janela); o `/usage` em dinheiro o dono confere. Onde foi maior: o relatório do subagente de protobufs (114 mil tokens dele) e as 4 rodadas por causa do QR.
- **O QR da Steam troca a cada ~20 s:** mostre numa janela que se atualiza (tkinter), não num PNG fixo. PNG aberto no visualizador trava a regravação (Errno 22).
- **Teste que mexe na conta precisa guardar o conteúdo, não só ids, depois de CADA passo:** o carrinho do dono (9 itens) terminou vazio e não deu para saber em que passo.

## 2026-10-04 — spec 04 inteira (Etapas 1, 1b, 1c e 2; v0.15.0)
- **Heredoc no Bash quebra com aspas, crases e `\`** (3 vezes: script cortado ou `\\` virando `\`). Para scripts de edição, use a ferramenta Write num arquivo `.py` no scratchpad e rode com `py -X utf8`; para trocas, `assert s.count(a) == 1` antes do `replace` (pegou todos os textos que não batiam).
- **Corte por índice apagou a `class Contexto` inteira** (fim = "próximo `\ndef`", mas o próximo era uma `class`). Corte só entre dois marcadores nomeados e rode `git diff --stat` logo depois: o −177 entregou o erro na hora.
- **Leituras grandes:** o `painel.html` foi lido em blocos de 100–200 linhas mais de uma vez. Mapeie antes (`tools/mapa.py`) e leia só a função que vai mudar; para achar código morto, um script que conta referências (função/const/classe CSS) é mais barato que ler.
- **Medir na fonte, não supor:** `IStoreQueryService/Query` sem `sort` repete itens entre páginas (70 mil "distintos" em 107.927; `sort: 2` resolve); o Edge headless não renderiza abaixo de ~500 px (para o celular, iframe de 390 px); Playwright num venv do scratchpad com `channel="msedge"` dispensa baixar navegador.
- **Pelo código, o `radar.py` usa a pasta do repositório** (sem banco): para teste real use `tools/rodar_instalado.py` (backup do banco antes). Para o painel numa cópia: `tools/painel_copia.py`. Datas em textos: `piso_ref.quando` é a última vez no *nível* (com folga de centavos), `quando_preco` é a do preço em si.

## 2026-10-04 — ajustes antes de publicar a 0.15.0
- **Teste real achou o que os testes sintéticos não acharam:** o toast do WRC 7 dizia "R$ 4,74, 10/2026" (data do nível, não do preço). Rodar o caminho real (`rodar_instalado.py`, toasts) antes de publicar vale o custo.
- **Releia a skill antes do último passo:** `novidades.md` ia com um comando de desenvolvedor; a skill `publicar-versao` proíbe. `gh` não existe aqui: acompanhe o workflow pela API pública (`api.github.com/repos/<repo>/actions/runs`).
- **Ao remover código morto, procure quem o usa também em `tools/`** (o `medir_spec04.py` quebrou com `raridade_ok` removido).

## 2026-10-04 — economia de tokens (configuração)
- **Criados:** `.claude/settings.json` (`model: opusplan`), subagentes `explorador` (Haiku, effort low) e `revisor` (Sonnet) e a skill do projeto `economia-de-contexto` (complementa a global).
- **Agente novo não carrega na sessão aberta** ("Agent type not found"): teste com `claude -p "..." --agent explorador --output-format json` (o prompt vem antes de `--allowedTools`, que engole argumentos).
- **Medido (explorador, "funções da aba Promoções"):** Haiku 4.5, 10 turnos, ~127 mil tokens de entrada (109 mil de cache) + 2,4 mil de saída, US$ 0,059. Achou `painel.html` 758–888 (22 funções).
- **O resumo veio com 28 linhas (tabela)**, não 15: a instrução do agente agora proíbe tabela e manda agrupar. Ainda não remedido.
- **ccusage e rtk:** `npm i -g ccusage` funciona (no PowerShell; `npx` pelo Git Bash falha). rtk 0.51.0 tem binário Windows (`%LOCALAPPDATA%\Programs\rtk`, checksum ok, telemetria desligada), mas o hook global (`rtk init -g`) mexe em `~/.claude/settings.json` e o modo automático bloqueia: o dono roda.
