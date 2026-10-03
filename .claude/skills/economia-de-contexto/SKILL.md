---
name: economia-de-contexto
description: Regras para gastar menos tokens e manter o contexto limpo ao programar - leitura por trechos, buscas antes de abrir arquivos, edições pequenas, saídas de comando resumidas, subagentes para buscas amplas, quando usar /compact e /clear. Use sempre que for ler arquivos grandes, rodar comandos com saída longa, a conversa estiver ficando extensa ou o usuário falar em economizar tokens/contexto.
---

# Economia de contexto

O contexto é o recurso mais caro: tudo que entra nele é relido a cada resposta.

## Ler
- **Buscar antes de abrir**: `grep -n "termo" arquivo` / `rg -n`. Depois leia só o intervalo (`sed -n '120,180p'` ou a leitura com faixa de linhas).
- **Mapa primeiro**: `py tools/mapa.py <arquivo> [termo]` dá seções e funções com linhas.
- **Nunca** despejar arquivos grandes (`painel.html` ~1.200 linhas, `referencia.md`, logs, `.json` de sonda). Use `head`, `tail -50`, `wc -l`, `grep -c`.
- **Não reler** um arquivo que você acabou de editar: confie no resultado da edição.
- **Docs antes do código**: `docs/referencia.md` (só a seção do módulo, via grep) responde "que funções existem" sem abrir o `.py`.

## Rodar comandos
- Corte a saída: `| tail -40`, `| head -20`, `| grep -E "erro|falh|ok"`.
- Prefira scripts que já resumem: `py tools/checar.py` (diz só o que falhou).
- Junte comandos relacionados numa chamada só (`a && b && c`).
- Para JSON grande: `python -c` que imprime só os campos/contagens que importam.

## Escrever
- Edições por substituição de trecho pequeno e único; nada de reescrever o arquivo inteiro.
- Não colar no chat o código que já está no arquivo; diga "editei X em `arquivo:linha`".
- Respostas ao usuário curtas: o que mudou, como testar, o que falta.

## Organizar a sessão
- **Uma funcionalidade por conversa.** Terminou e foi publicada → `/clear` e conversa nova.
- Conversa ficou longa mas a tarefa continua → `/compact` com um foco ("mantenha só as decisões sobre o carrinho").
- **Buscas amplas** ("onde isso é usado no projeto todo?") → mande um subagente (Explore/Task) e receba só o resumo.
- Decisões que precisam sobreviver à conversa vão para `docs/decisoes.md`, não ficam só no chat.

## Sinais de desperdício (pare e corrija)
- Você leu o mesmo arquivo 2+ vezes na tarefa.
- Saída de comando com mais de ~80 linhas.
- Você está "explorando" sem hipótese. Volte ao plano.
