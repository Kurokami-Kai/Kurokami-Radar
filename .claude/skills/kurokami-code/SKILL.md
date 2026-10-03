---
name: kurokami-code
description: Fluxo padrão para qualquer tarefa de programação no Kurokami Radar (funcionalidade nova, correção, ajuste visual, refatoração). Use SEMPRE no início de uma tarefa de código neste repositório, mesmo que o pedido pareça pequeno; ela diz qual outra skill abrir e em que ordem trabalhar.
---

# Kurokami Code — por onde começar

Esta skill **não carrega as outras**: ela indica qual abrir. Abra só a que a tarefa precisa.

## 1. Entender antes de tocar (barato)
- Leia o `CLAUDE.md` (já está no contexto) e **só** o doc de `docs/` que a tarefa pede.
- Para achar código: `py tools/mapa.py <arquivo> [termo]` e leia apenas o intervalo de linhas indicado. Nunca abra `painel.html` ou `docs/referencia.md` inteiros.
- Mexe em coleta, preços, avaliação ou instalador? Leia `docs/decisoes.md` primeiro.

## 2. Plano curto
Antes de editar, escreva em 3 a 8 linhas: o que muda, em quais arquivos, como testar. Se a tarefa for grande ou ambígua, mostre o plano ao usuário e espere o ok.

## 3. Qual skill abrir
| A tarefa mexe em… | Abra |
|---|---|
| economizar contexto/tokens, arquivo grande, conversa longa | `economia-de-contexto` |
| `painel.html` (visual, abas, JS do painel) | `editar-painel` |
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
