---
name: revisar-mudanca
description: Checklist final antes de dar tarefa por concluída (checagens, revisão do diff, docs, versão, o que testar no Windows). Use ao terminar qualquer mudança de código, antes de dizer "pronto".
---

# Revisar mudança

Regra de ouro (de `verification-before-completion`, obra/superpowers, se instalada): **nada de "pronto", "funciona" ou "corrigido" sem ter rodado o comando que prova isso nesta mesma resposta.**

1. `py tools/checar.py` → precisa terminar em `ok`. (Sintaxe Python, JS do painel, VERSAO = VERSAO_PAGINA, `--add-data`, dados pessoais.)
2. `git diff --stat` e depois `git diff` só dos arquivos tocados. Procure:
   - texto de dado sem `esc()` no painel; dinheiro fora de centavos; data sem UTC;
   - chamada de API sem tratar falha; laço longo sem `progresso.passo`;
   - leitura de "preço atual" fora de `oferta_atual`;
   - caminhos fixos que quebram no `.exe` (use `radar/caminhos.py`).
3. Arquivo novo lido pelo `.exe` → `--add-data` (o checar acusa).
4. `docs/referencia.md` só se regenera ao publicar versão (skill `publicar-versao`).
5. **Ajuste só visual** (cor, espaçamento, posição, texto): só uma linha na seção de cima de `docs/novidades.md`; pule o resto deste passo e o revisor. Comportamento mudou para o usuário → `README.md`. Mudou rota/dado/arquitetura → doc em `docs/`. Pegadinha nova → `docs/decisoes.md`.
6. Com o `checar` em `ok` → commit e push **sem perguntar** (ver `CLAUDE.md`). Só pergunte antes de `reset`, `rebase`, `push --force` ou de apagar arquivos fora do projeto.
7. Vai virar release? → skill `publicar-versao`.
8. Resposta final ao usuário (curta):
   - o que mudou (3 a 6 itens);
   - **como testar no Windows** (passos);
   - o que você **não** conseguiu testar (notificação, bandeja, carrinho direto, instalador…).
   (Não há mais passo de "Docs para atualizar no Projeto": o Projeto do claude.ai lê os docs do GitHub.)
