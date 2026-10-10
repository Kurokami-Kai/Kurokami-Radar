# Kurokami Hunter — instruções para o Claude Code

App local de Windows (Python 3.12): monitora a lista de desejos da Steam em várias lojas, guarda histórico em SQLite, notifica no Windows e serve um painel em `http://localhost/kurokami`. Usuários: o dono e amigos, via instalador do GitHub Releases. Responda e escreva mensagens/UI em **português**.

## Docs (leia só o que a tarefa pede)

- `docs/aprendizados.md` — até 40 linhas; leia no início de tarefa de código. Só acrescente uma linha ao achar armadilha que vai se repetir.
- `docs/decisoes.md` — **antes de mexer em coleta, preços, avaliação ou instalador, leia a seção da tarefa** (`grep -n '^## '` e só o intervalo; nunca o arquivo inteiro). Armadilhas que já foram bugs reais e preferências de produto.
- `docs/estrutura.md` — o que cada arquivo/pasta contém e onde ficam os dados.
- `docs/arquitetura.md` — threads, ciclo de coleta, fontes e limites, avaliação, notificação, painel, carrinho pela extensão, distribuição.
- `docs/api.md` — rotas HTTP do painel; consulte ao mexer em `painel.py` ou no painel.
- `docs/dados.md` — tabelas SQLite, chaves de `meta`, `config.json`, segredos.
- `docs/referencia.md` — assinaturas e docstrings (gerado; nunca inteiro; `py tools/gerar_referencia.py` só ao publicar).
- `docs/processo.md` — rodar, testar, publicar; convenções de código.
- `docs/novidades.md` — texto da próxima versão; acrescente ao mudar algo visível. Leia só a seção de cima.
- `docs/pendencias.md` — ideias combinadas, com links para `docs/specs/NN-*.md`. Ao implementar uma spec, leia só a dela e marque "feito em vX.Y.Z".
- `tools\exportar_docs.py` — reserva, fora do fluxo (o Projeto do claude.ai lê os docs do GitHub); só se o dono pedir.

## Ferramentas e skills

- Comece tarefas de código pela skill **`kurokami-code`** (indica qual outra abrir). Demais em `.claude/skills/`: `economia-de-contexto`, `editar-painel`, `coleta-e-apis`, `banco-e-migracao`, `depurar`, `testar-sem-rede`, `revisar-mudanca`, `publicar-versao`.
- Leitura ampla e testes: subagente `explorador`; revisão de diff: `revisor`.
- `py tools/mapa.py <arquivo ou pasta> [termo]` → seções/funções com linhas; leia só o intervalo. O painel é `radar/painel.html` (só HTML) + `radar/painel-web/` (CSS e JS, um arquivo por seção; `painel.py` troca cada `/*incluir x*/` pelo arquivo e entrega uma página só). Nunca abra `ficha.js`, `ofertas.html` ou `biblioteca.html` inteiros.
- Abas Ofertas e Biblioteca = `radar/ofertas.html` e `radar/biblioteca.html` (páginas num iframe, dados de `radar/ofertas.py`); falam com o painel por `parent.KH` (`docs/arquitetura.md`, "Ofertas e Biblioteca").
- `py tools/checar.py` → checagens finais (sintaxe, JS, versão, `--add-data`, `tools/testar_piso.py`, dados pessoais: falha se `config.json`, `userdata.json` ou `dados/` estiverem rastreados ou faltarem no `.gitignore`). Precisa dar `ok`.

## Regras do projeto

- Versão: `VERSAO` em `radar/__init__.py` e `VERSAO_PAGINA` em `radar/painel-web/status.js` mudam **juntas**.
- Login Steam: "Entrar pela Steam" (OpenID) guarda só o SteamID; o carrinho vai pela extensão própria (`extensao/`), que usa a sessão da página da Steam; o QR saiu na 0.16. Senha, token e cookie da Steam nunca em arquivo, log, banco ou Git (`docs/decisoes.md`, "Login Steam").
- "Preço de agora" vem de `oferta_atual`/`Banco.ofertas_atuais()`, nunca do último registro de `preco`.
- Dinheiro em centavos; datas em UTC ISO.
- Nada pessoal no repositório: `config.json`, `userdata.json` e `dados/` no `.gitignore`; chaves só no keyring.
- Arquivo novo que o `.exe` precise ler → `--add-data` do workflow e do `gerar_setup.bat`.
- Visual do painel segue a loja da Steam, **só preto e vermelho**, cada vermelho com um papel (`--acao` compra, `--sinal` ativo/importante, `--blue` texto clicável), botões secundários cinza e **escala de calor** no desconto e nas etiquetas (`data-calor`); símbolo em preto e vermelho (`docs/decisoes.md`, "Produto", "Paleta por papel").
- Nome visível: **Kurokami Hunter**. Pasta de dados, keyring, `KurokamiRadar.exe`, instalador, repositório e pacote `radar/` mantêm o nome antigo de propósito (`docs/decisoes.md`, "Produto"): não renomeie.
- Depois de mudar comportamento, atualize **sem perguntar**, na mesma tarefa: este `CLAUDE.md` (se afetar algo daqui), o `README.md` (usuário) e os docs afetados. **Ajuste só visual** (cor, espaçamento, posição, texto de botão): só uma linha em `docs/novidades.md`, sem README, outros docs nem revisor.
- Ao terminar cada tarefa, com `py tools/checar.py` em `ok`: commit e push **sem perguntar**. Pergunte só antes de comandos que reescrevem histórico (`reset`, `rebase`, `push --force`) ou apagam arquivos fora do projeto.
- **Publicar = você cria e envia a tag `vX.Y.Z`**, só quando o dono disser "publique". Antes: `VERSAO`/`VERSAO_PAGINA` iguais e a seção `## X.Y.Z` em `docs/novidades.md` (vira a descrição do release; sem ela o workflow falha). Skill `publicar-versao`.
