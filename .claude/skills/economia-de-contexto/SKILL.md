---
name: economia-de-contexto
description: Regras de economia de tokens do Kurokami Radar - painel.html só por função (tools/mapa.py), leitura/testes no subagente explorador, revisão no revisor, /clear e /compact, docs por seção, relatório enxuto e esforço por tipo de tarefa. Use sempre que for ler arquivos grandes, buscar, testar, revisar diff ou a conversa estiver longa.
---

# Economia de contexto (Kurokami Radar)

Complementa a skill geral `~/.claude/skills/economia-de-contexto` (buscar antes de abrir, ler por trechos, cortar saídas, não reler o que editou). Aqui ficam só as regras deste projeto.

## Ler
- `radar/painel.html` (~1.300 linhas, muitas longas) **nunca** é lido inteiro: `py tools/mapa.py radar/painel.html [termo]`, ache a função e leia só o intervalo dela (offset/limit).
- `docs/` não se lê inteiro: abra só o doc do assunto (ver `CLAUDE.md`) e só a seção necessária (`py tools/mapa.py docs/x.md` ou `Grep` no título).

## Delegar
- Leitura ampla, busca, mapa, código morto, `py tools/checar.py` e testes de `tools/` → subagente **`explorador`** (Haiku; devolve até 15 linhas com `caminho:linha`).
- Revisão de diff (`git diff <a>..<b>`) → subagente **`revisor`** (Sonnet; lista erro claro / código morto / sugestão).

## Sessão
- Uma sessão nova (`/clear`) a cada parte de spec (Etapa 1, 1b, 2…).
- `/compact` quando a conversa passar de uns 40 turnos, dizendo o que manter.
- Modelo do projeto: `opusplan` (Opus no planejamento, Sonnet na execução).

## Medir
- `ccusage daily` / `ccusage session` (npm global; rode no PowerShell, no Git Bash o `node` não acha) antes e depois de uma mudança de processo.
- Se o `rtk` estiver instalado (hook global do usuário), os comandos do Bash já saem comprimidos; `rtk gain` mostra a economia. Não instale hook do rtk no `.claude/` do repositório: quem clonar sem rtk ficaria com o hook quebrado.

## Esforço
- Baixo para tarefa mecânica: docs, renomear, rodar testes.
- Alto só para regra de negócio (preço, piso, avaliação, coleta).

## Relatório final
Nada de "relatório bonito": só o que mudou, os números pedidos e o que não foi testado.
