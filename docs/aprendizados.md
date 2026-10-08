# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

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
