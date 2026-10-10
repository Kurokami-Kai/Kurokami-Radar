# Aprendizados

Só lições que continuam valendo (o diário de cada tarefa fica no `git log`). Acrescente uma linha quando achar uma armadilha que vai se repetir; ajuste visual comum não entra. Máximo de 40 linhas: ao passar, junte ou apague as que perderam valor.

## Investigar
- **Medir antes de propor:** contar no banco ou na API (quantos mudam, quantos o filtro pega) antes de criar regra, métrica ou coluna; conferir 3 itens na loja antes de perseguir contagem de terceiros.
- **Ler o log e o estado antes do código:** `grep "biblioteca:" radar.log`, `netstat -ano | findstr LISTENING` (várias cópias na mesma porta: o `HTTPServer` do Windows liga `SO_REUSEADDR`; o `painel.py` usa `allow_reuse_address=False`), pasta da extensão em qual navegador.
- **"Contraditório" costuma ser duas definições do mesmo termo** (ex.: "esta promoção" em `analise` × `previsao`): imprimir os dados do jogo do print num script do scratchpad acha em 1 rodada.
- **Empate escolhe a primeira linha do banco:** ao mostrar "a loja do melhor preço", desempate pela Steam.
- `GetOwnedGames` não traz DLCs (só o `rgOwnedApps` da extensão); a ITAD tem cota (~100 chamadas em 5 min: espaçar e parar no primeiro 429).

## Painel e navegador do app
- **Conferir pelo DOM, não por print:** `getComputedStyle`, `getBoundingClientRect`, `elementFromPoint` e laços (opção × aba × modo) acham sobra de cor, desalinhamento e cobertura mais barato; print fica para o fim.
- **Um `<script>` só** (o `painel.py` junta os arquivos): `function` vale antes de onde está escrita, `const`/`let` não (TDZ); `function x` no topo já é `window.x` (embrulho com o mesmo nome vira recursão).
- **Classes novas com prefixo da aba** (`cfg-…`): `.crow` colidiu com o carrinho; ache regras que casam por `cssRules` + `matches`.
- **Navegação:** `navigate` para outro `#` não recarrega (use `location.reload()` ou `?v=N`); o painel abre na última aba salva (clique no menu); `ref_N` vence ao navegar (rode `find` de novo); pane escondida mede zero (`resize_window` antes).
- **Teclas:** foco no painel não chega no iframe (repasse por `window.buscar`); AltGr chega como Ctrl+Alt.
- `window.open` com `noopener` sempre devolve `null`; o Chrome libera uma aba por clique.
- Arquivo local acima de ~512 KB não abre no navegador do app; amostras com dado pessoal vão para `dados/`.
- Porta 8801 ocupada por outra conversa: entrada temporária no `launch.json` e `git checkout` dele antes do commit.

## Editar arquivos
- **Scripts de edição pelo Write num `.py` do scratchpad** (heredoc quebra aspas, crases, `\` e `\\n`), com `assert s.count(a) == 1` antes de cada troca e `git diff --stat` depois; trocas com escapes, pelo Edit.
- **CRLF:** `git checkout` e scripts em modo texto trocam fim de linha; normalize `\r\n` ao ler e grave igual.
- **Troca em massa protege identificadores** (keyring, pasta, exe): conferir com `git grep` depois; `${}` em aspas simples não interpola.
- **Limpar código morto por regra, não por linha**, procurando também nomes montados no JS (`pp-${t}`) e em `tools/`.
- Nunca terminar comando com `cat` sem arquivo (trava esperando entrada); `Set-Content` grava BOM: commit com `git commit -F`.

## Testar
- Testar mesmo quando parece simples (o "Esc" quebrou o `/` inteiro).
- Lógica sem rede: cópia do banco + chamar `painel.api_*` direto; `tools/rodar_instalado.py` acha o que os sintéticos não acham.
- Não rodar coleta pelo app do dono para encher amostra (API de listagem + banco em modo leitura).
- O revisor em paralelo com os docs pegou erros reais várias vezes: vale em mudança de lógica.
- A loja do Edge recusa `description` acima de 132 caracteres no `manifest.json` (o `checar.py` confere).

## Economia de tokens
- Modelo padrão Sonnet (`.claude/settings.json`); Opus só para planejar algo grande. Conversa nova perto de 100–150k tokens ou ao trocar de assunto; `/compact` no meio de uma tarefa.
- `decisoes-<assunto>.md` (índice em `decisoes.md`) e `novidades.md` por seção, nunca inteiros; `referencia.md` só se regenera ao publicar.
- Subagentes: `explorador` (Haiku) para leitura ampla, `revisor` (Sonnet) para diff de lógica.
