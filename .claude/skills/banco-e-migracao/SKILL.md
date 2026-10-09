---
name: banco-e-migracao
description: Como mudar o banco SQLite e o config.json do Kurokami Hunter sem quebrar instalações existentes (colunas, tabelas, chaves de meta, migração de dados, configurações novas). Use sempre que a tarefa precisar guardar um dado novo, mudar formato de dado ou adicionar opção de configuração.
---

# Banco e migração

Os usuários já têm bancos com meses de histórico. **Nenhuma mudança pode exigir apagar o banco.**

## Coluna ou tabela nova
- Tabela nova: `CREATE TABLE IF NOT EXISTS` no `ESQUEMA` (`radar/banco.py`).
- Coluna nova: acrescente o `ALTER TABLE ... ADD COLUMN` na lista tolerante de `Banco.__init__` (erro de "já existe" é ignorado). Se a coluna vem do catálogo, inclua no `cols` de `salvar_jogo`.
- Nunca renomeie/apague coluna: crie a nova e pare de usar a velha.

## Dados existentes
- Converter dados antigos: bloco em `_migrar()` protegido por `meta.esquema` (incremente o número). Rode uma vez, rápido, e faça `commit`.
- Estado interno pequeno: `banco.meta("chave", valor)` (JSON). Liste a chave nova em `docs/dados.md`.

## Configuração nova
- Só adicionar em `config.PADRAO` (o `carregar()` faz merge — arquivos antigos ganham o padrão sozinhos).
- Mudar o padrão de chave que **já existe** não chega a quem já tem o `config.json`: acrescente uma entrada em `config.MIGRACOES` (roda uma vez; depois vale a escolha do usuário).
- Se o painel edita: campo em `renderCfg` (`painel-web/configuracoes.js`) e chave permitida em `post_config` (`painel.py`).
- Nunca guardar segredo no config (use `credenciais`).

## Regras de dado
- Dinheiro em centavos (int). Datas `banco.utc()`/`agora()` (ISO UTC). Brindes (R$ 0) não contam como preço.
- Transações curtas: o painel grava ao mesmo tempo (`timeout=30`). Arquivo que muda muito pelo painel (ex.: carrinho) pode ir para `dados/*.json`.

## Testar
Copie um banco real (`dados/radar.sqlite3`), abra `Banco()` nele e confira que a migração roda e o painel (`api_lista`, `api_jogo`) continua respondendo. Atualize `docs/dados.md`.
