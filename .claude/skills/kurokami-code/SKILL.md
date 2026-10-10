---
name: kurokami-code
description: Fluxo padrão de qualquer tarefa de código no Kurokami Hunter (funcionalidade, correção, ajuste visual, refatoração); diz qual outra skill abrir. Use SEMPRE no início de tarefa de código neste repositório, mesmo pequena.
---

# Kurokami Code — por onde começar

Esta skill **não carrega as outras**: ela indica qual abrir. Abra só a que a tarefa precisa.

## 1. Entender antes de tocar (barato)
- Leia o `CLAUDE.md` (já está no contexto) e **só** o doc de `docs/` que a tarefa pede.
- Para achar código: `py tools/mapa.py <arquivo> [termo]` e leia apenas o intervalo de linhas indicado. Nunca abra `ficha.js`, `ofertas.html` ou `docs/referencia.md` inteiros (`py tools/mapa.py radar/painel-web [termo]`).
- Mexe em coleta, preços, avaliação ou instalador? Abra só o `docs/decisoes-<assunto>.md` da tarefa (índice em `docs/decisoes.md`).

## 2. Plano curto
Antes de editar, escreva em 3 a 8 linhas: o que muda, em quais arquivos, como testar. Se a tarefa for grande ou ambígua, mostre o plano ao usuário e espere o ok.

## 3. Qual skill abrir
| A tarefa mexe em… | Abra |
|---|---|
| economizar contexto/tokens, arquivo grande, conversa longa | `economia-de-contexto` |
| `painel.html`/`painel-web/` (visual, abas, JS do painel) | `editar-painel` |
| `steam.py`, `itad.py`, `ggdeals.py`, `coleta.py`, `rede.py` | `coleta-e-apis` |
| tabelas, colunas, `meta`, `config.json` | `banco-e-migracao` |
| bug, erro do usuário, log, comportamento estranho | `depurar` (+ `systematic-debugging`, global) |
| testar sem chamar as APIs | `testar-sem-rede` |
| testar o painel no navegador (prints, cliques) | `webapp-testing` (global, Anthropic) |
| terminar a tarefa | `revisar-mudanca` (+ `verification-before-completion`, global) |
| lançar versão / release | `publicar-versao` |

## 4. Implementar
- Mudança mínima que resolve. Edite com substituições pequenas, não reescreva arquivos.
- Siga as convenções de `docs/processo.md` (centavos, UTC, português, tolerar falhas de API).

## 5. Fechar
Abra `revisar-mudanca`: roda `py tools/checar.py`, revisa o diff, atualiza docs e README. Termine com um resumo curto para o usuário: o que mudou, como testar no Windows, o que você não conseguiu testar.
