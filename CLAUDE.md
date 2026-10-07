# Kurokami Radar — instruções para o Claude Code

App local de Windows (Python 3.12) que monitora a lista de desejos da Steam em várias lojas, guarda histórico em SQLite, notifica no Windows e serve um painel em `http://localhost/kurokami`. Usuários: o dono do repositório e amigos, via instalador do GitHub Releases. Responda e escreva mensagens/UI em **português**.

## Leia antes de mexer

Leia só o que a tarefa pede, nesta ordem de utilidade:

- Leitura e testes: subagente explorador; revisão de diff: revisor; painel.html só por função (tools/mapa.py); regras em .claude/skills/economia-de-contexto.
- `docs/aprendizados.md` — leia no início de toda tarefa; atualize no fim.
- `docs/decisoes.md` — **sempre leia antes de mexer em coleta, preços, avaliação ou instalador.** Lista armadilhas que já foram bugs reais (preço "atual", fusos, pacote base, GG.deals, versão da página etc.) e as preferências de produto.
- `docs/estrutura.md` — o que cada arquivo e pasta contém e onde ficam os dados. Consulte para achar onde ler, editar ou criar algo.
- `docs/arquitetura.md` — como as peças conversam: threads, ciclo de coleta, fontes de dados e seus limites, avaliação, notificação, painel, ponte, distribuição e atualização.
- `docs/api.md` — rotas HTTP do painel (GET/POST), campos e regras de acesso. Consulte ao mexer em `painel.py` ou `painel.html`.
- `docs/dados.md` — tabelas SQLite, chaves de `meta`, `config.json` e onde ficam os segredos.
- `docs/referencia.md` — assinaturas e docstrings de todas as funções (gerado; rode `py tools/gerar_referencia.py` depois de mudar funções).
- `docs/processo.md` — rodar, testar e publicar versão; convenções de código.
- `docs/novidades.md` — novidades da próxima versão (texto do release); acrescente ao mudar algo visível.
- `docs/pendencias.md` — ideias combinadas e ainda não feitas; aponta para `docs/specs/`.
- `docs/specs/NN-*.md` — especificação de cada funcionalidade pedida (problema, dados reais, proposta, critérios de aceite). **Ao implementar uma, leia só a spec dela.** Ao terminar, marque o Status como "feito em vX.Y.Z".

## Ferramentas e skills

- Comece tarefas de código pela skill **`kurokami-code`** (ela diz qual outra skill abrir; não carrega todas).
- `py tools/mapa.py <arquivo> [termo]` → seções/funções com linhas; leia só o intervalo. Nunca abra `radar/painel.html` inteiro.
- `py tools/checar.py` → checagens finais (sintaxe, JS, versão, `--add-data`, `tools/testar_piso.py`, dados pessoais e `.gitignore`: falha se `config.json`, `userdata.json` ou `dados/` estiverem rastreados pelo Git ou faltarem no `.gitignore`). Precisa dar `ok`.
- `tools\exportar_docs.py` → **reserva, fora do fluxo**: o Projeto do claude.ai lê os docs direto do GitHub. Só use se o dono pedir.
- Skills em `.claude/skills/`: `kurokami-code`, `economia-de-contexto`, `editar-painel`, `coleta-e-apis`, `banco-e-migracao`, `depurar`, `testar-sem-rede`, `revisar-mudanca`, `publicar-versao`.

## Regras do projeto

- Versão: `VERSAO` em `radar/__init__.py` e `VERSAO_PAGINA` em `radar/painel.html` mudam **juntas**.
- Login Steam: "Entrar pela Steam" (OpenID) guarda só o SteamID; o QR opcional (`steam_sessao.py`) guarda o refresh token só no cofre do Windows. Senha, token e cookie da Steam nunca em arquivo, log, banco ou Git (ver `docs/decisoes.md`, "Login Steam").
- "Preço de agora" vem de `oferta_atual`/`Banco.ofertas_atuais()`, nunca do último registro de `preco`.
- Dinheiro em centavos; datas em UTC ISO.
- Nada pessoal no repositório: `config.json`, `userdata.json` e `dados/` estão no `.gitignore`. Chaves só no keyring.
- Arquivo novo que o `.exe` precise ler → adicionar ao `--add-data` do workflow e do `gerar_setup.bat`.
- Visual do painel segue a loja da Steam (ver `docs/decisoes.md`, "Produto").
- Depois de mudar comportamento: atualize **você mesmo, sem perguntar**, o `CLAUDE.md` (se a mudança afetar algo descrito aqui), o `README.md` (usuário) e os docs afetados em `docs/`, no mesmo trabalho da mudança.
- Ao terminar cada tarefa, depois de `py tools/checar.py` dar `ok`: faça o commit e o push **sem perguntar**. Só pergunte antes de comandos que reescrevem histórico (`reset`, `rebase`, `push --force`) ou que apagam arquivos fora do projeto.
- **Publicar = você cria e envia a tag `vX.Y.Z`**, só quando o dono disser "publique". Antes: `VERSAO`/`VERSAO_PAGINA` iguais e a seção `## X.Y.Z` em `docs/novidades.md` (vira a descrição do release; sem ela o workflow falha). Ver skill `publicar-versao`.
