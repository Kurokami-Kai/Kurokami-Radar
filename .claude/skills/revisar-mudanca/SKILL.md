---
name: revisar-mudanca
description: Checklist final antes de dar uma tarefa do Kurokami Radar por concluída (checagens automáticas, revisão do diff, docs, versão, o que testar no Windows). Use sempre ao terminar qualquer mudança de código, antes de responder "pronto" ao usuário.
---

# Revisar mudança

Regra de ouro (de `verification-before-completion`, obra/superpowers, se instalada): **nada de "pronto", "funciona" ou "corrigido" sem ter rodado o comando que prova isso nesta mesma resposta.**

1. `py tools/checar.py` → precisa terminar em `ok`. (Sintaxe Python, JS do painel e da ponte, VERSAO = VERSAO_PAGINA, `--add-data`, dados pessoais.)
2. `git diff --stat` e depois `git diff` só dos arquivos tocados. Procure:
   - texto de dado sem `esc()` no painel; dinheiro fora de centavos; data sem UTC;
   - chamada de API sem tratar falha; laço longo sem `progresso.passo`;
   - leitura de "preço atual" fora de `oferta_atual`;
   - caminhos fixos que quebram no `.exe` (use `radar/caminhos.py`).
3. Arquivo novo lido pelo `.exe` → `--add-data` (o checar acusa).
4. Função pública nova/alterada → `py tools/gerar_referencia.py`.
5. Comportamento mudou para o usuário → `README.md`. Mudou rota/dado/arquitetura → doc em `docs/`. Pegadinha nova → `docs/decisoes.md`.
6. Vai virar release? → skill `publicar-versao`.
7. Resposta final ao usuário (curta):
   - o que mudou (3 a 6 itens);
   - **como testar no Windows** (passos);
   - o que você **não** conseguiu testar (notificação, bandeja, ponte, instalador…).
