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
6. `docs/novidades.md` tem a seção `## X.Y.Z` com o texto do release (é a descrição publicada e aparece na janela de atualização; escreva para o usuário, sem comandos de desenvolvedor).
7. Commit e push (`git add -A && git commit -m "vX.Y.Z: resumo" && git push`).
8. **Só se o dono disse "publique":** `git tag vX.Y.Z && git push origin vX.Y.Z`. O workflow confere tag × `VERSAO` e a seção das novidades (falha com mensagem clara se faltar), gera o `Setup.exe` e publica o release com a descrição e o instalador.
9. Acompanhe o workflow até o fim (página Actions/Releases do repositório) e confirme ao dono que o release tem a descrição e o `Setup.exe`. Os Radars instalados avisam ao abrir ou em até 24 h.
