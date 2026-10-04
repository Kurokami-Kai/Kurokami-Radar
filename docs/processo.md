# Como desenvolver, testar e publicar

## Rodar pelo código
```
py -m pip install -r requirements.txt
py radar.py chaves            # perfil + chaves (janela)
pyw radar.py bandeja --abrir  # app completo
py radar.py painel            # só o painel (sem coleta)
py radar.py verificar         # uma coleta no terminal, sem notificar
py radar.py sondar 1659040    # respostas cruas das APIs em dados/sonda/sonda.json
```
Com o Radar instalado aberto, feche-o antes (porta 80 e trava 47811 são compartilhadas).

## Testes rápidos
- **Tudo de uma vez:** `py tools/checar.py` (também falha se `config.json`, `userdata.json` ou `dados/` estiverem rastreados pelo Git ou faltarem no `.gitignore`, e roda `tools/testar_piso.py`).
- **Raridade e pílula de piso:** `py tools/testar_piso.py` — históricos sintéticos (Recorde raro em 17/19 meses e 50%, Lendário pela regra C). Mudou a regra? Acrescente o caso aqui.
- **Backtest do Selo:** `py tools/backtest_selo.py` (≈ 30 s) — semana a semana, só com o histórico conhecido até a data; mede "não batido" em 12 meses (+5/+10), "não voltou" em 6 meses e Selos por semana, para as variantes A–H, "F ou G" e duas linhas de base. Lê uma cópia temporária do banco.
- **Toast de Selo:** `py radar.py testar-notificacao --selo` (pega um Selo de verdade do seu banco e passa pelo `Notificador._enviar`, como numa rodada).
- Sintaxe: `py -c "import ast,glob;[ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('radar/*.py')+['radar.py']]"`
- JS do painel: extrair o `<script>` de `painel.html` e rodar `new Function(js)` no Node.
- Lógica sem rede: copiar um `dados/radar.sqlite3` real e chamar `painel.api_lista({})`, `api_jogo`, `api_carrinho`, `analise.avaliar` com `b.ofertas_atuais()`.
- Visual: subir `py radar.py painel` e tirar prints com Playwright em `http://127.0.0.1/kurokami`.
- O que só dá para testar no Windows real: notificações, bandeja, instalador, ponte na Steam, atualização silenciosa.

## Publicar uma versão
1. Mudar `VERSAO` em `radar/__init__.py` **e** `VERSAO_PAGINA` em `radar/painel.html` (mesmo número).
2. Se mudou função pública: `py tools/gerar_referencia.py`.
3. Atualizar `README.md`/docs se o comportamento mudou para o usuário.
4. Escrever a seção `## X.Y.Z` em `docs/novidades.md` (o título pode ter complemento, ex.: `## 0.14.0 (publicada em 2026-10-04)`). O texto dela, sem o título e até o próximo `## `, vira a **descrição do release** — é o que aparece na janela de atualização.
5. Commit/push no GitHub.
6. **Só quando o dono disser "publique":** o Claude Code cria e envia a tag (`git tag vX.Y.Z && git push origin vX.Y.Z`). O workflow `gerar-instalador.yml`:
   - falha com mensagem clara se a tag não bate com `VERSAO` ou se `docs/novidades.md` não tem a seção `## X.Y.Z` (ou ela está vazia);
   - gera o `Setup.exe` e publica o release com a descrição e o instalador anexado.
7. Os Radars instalados avisam ao abrir ou em até 24 h.

Arquivos novos que o `.exe` precisa ler (como `painel.html`, `ponte.user.js`) devem entrar no `--add-data` do workflow **e** do `gerar_setup.bat`.

## Exportar a documentação (reserva)
O Projeto "Kurokami Radar" no claude.ai lê os docs **direto do GitHub**: não é preciso atualizá-lo à mão, e o fim de cada tarefa não tem mais o passo "Docs para atualizar no Projeto". O `tools/exportar_docs.py` fica no repositório só como reserva (por exemplo, se o Projeto voltar a usar arquivos enviados):
1. Dois cliques em `tools\exportar_docs.bat` (ou `py tools/exportar_docs.py`).
2. Ele copia `CLAUDE.md`, `README.md`, `docs/*.md` (menos `referencia.md`) e `docs/specs/*.md` para `Área de Trabalho\kurokami-docs\todos`. Só o que é **novo ou mudou** desde a última exportação vai para `...\enviar`. Os nomes ficam achatados, como `docs-decisoes.md` e `spec-02-....md`.
3. A tela lista os arquivos NOVOS, ALTERADOS e APAGADOS. No Projeto, remova as versões antigas dos alterados e apagados e envie a pasta `enviar`.
4. Digite **S** para registrar a exportação (em `kurokami-docs\.ultima_exportacao.json`). Sem o S, nada é registrado e a próxima exportação mostra as mesmas mudanças.

`py tools/exportar_docs.py --listar` só lê: mostra o que mudou desde a última exportação **confirmada**, sem copiar, perguntar nem registrar. Não faz parte do fluxo obrigatório.

## Convenções de código
- Python 3.12, só stdlib + keyring/pystray/Pillow. Sem frameworks.
- Português em nomes, comentários e mensagens (sem acentos em identificadores).
- Dinheiro em centavos; datas UTC ISO; logs curtos via a função `log` recebida (vira progresso no painel: linha sem recuo = etapa nova).
- Toda chamada externa tolera falha e segue (lote recusado não derruba a coleta).
- Colunas novas: `ALTER TABLE` tolerante; config novo: só adicionar em `PADRAO`.
