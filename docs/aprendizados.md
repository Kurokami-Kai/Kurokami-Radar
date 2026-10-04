# Aprendizados

Leia no início de toda tarefa; atualize no fim (até 5 linhas datadas: o que gastou tokens à toa, erros que se repetiram, o que fazer diferente). Máximo de 60 linhas: quando passar, resuma as entradas antigas num bloco só.

## 2026-10-04 — spec 04 inteira (Etapas 1, 1b, 1c e 2; v0.15.0)
- **Heredoc no Bash quebra com aspas, crases e `\`** (3 vezes: script cortado ou `\\` virando `\`). Para scripts de edição, use a ferramenta Write num arquivo `.py` no scratchpad e rode com `py -X utf8`; para trocas, `assert s.count(a) == 1` antes do `replace` (pegou todos os textos que não batiam).
- **Corte por índice apagou a `class Contexto` inteira** (fim = "próximo `\ndef`", mas o próximo era uma `class`). Corte só entre dois marcadores nomeados e rode `git diff --stat` logo depois: o −177 entregou o erro na hora.
- **Leituras grandes:** o `painel.html` foi lido em blocos de 100–200 linhas mais de uma vez. Mapeie antes (`tools/mapa.py`) e leia só a função que vai mudar; para achar código morto, um script que conta referências (função/const/classe CSS) é mais barato que ler.
- **Medir na fonte, não supor:** `IStoreQueryService/Query` sem `sort` repete itens entre páginas (70 mil "distintos" em 107.927; `sort: 2` resolve); o Edge headless não renderiza abaixo de ~500 px (para o celular, iframe de 390 px); Playwright num venv do scratchpad com `channel="msedge"` dispensa baixar navegador.
- **Pelo código, o `radar.py` usa a pasta do repositório** (sem banco): para teste real use `tools/rodar_instalado.py` (backup do banco antes). Para o painel numa cópia: `tools/painel_copia.py`. Datas em textos: `piso_ref.quando` é a última vez no *nível* (com folga de centavos), `quando_preco` é a do preço em si.
