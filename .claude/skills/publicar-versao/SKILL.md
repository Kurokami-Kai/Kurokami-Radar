---
name: publicar-versao
description: Prepara uma versão nova do Kurokami Radar para o GitHub Releases (número de versão nos dois lugares, checagens, referência, docs, texto do release). Use quando o usuário pedir para "lançar", "publicar", "fechar versão", "subir para o GitHub" ou "gerar o instalador".
---

# Publicar versão

1. Número novo `MAJOR.MINOR.PATCH` (correção = PATCH, função nova = MINOR). Confirme com o usuário se não for óbvio.
2. Atualize juntos: `VERSAO` em `radar/__init__.py` e `VERSAO_PAGINA` em `radar/painel.html`.
3. `py tools/gerar_referencia.py` se funções mudaram.
4. `py tools/checar.py` → `ok`.
5. README/docs coerentes com o que mudou.
6. Commit e push (`git add -A && git commit -m "vX.Y.Z: resumo" && git push`).
7. Diga ao usuário: **Releases → Draft a new release → tag `vX.Y.Z` → Publish**. O workflow gera o `Setup.exe` e anexa; os Radars instalados avisam ao abrir ou em até 24 h.
8. Entregue 3 a 6 linhas de novidades (parta de `docs/novidades.md`) para a descrição do release (aparecem na janela de atualização).
