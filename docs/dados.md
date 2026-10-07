# Dados: banco, config e chaves

Valores de dinheiro são **centavos (int)**. Datas no banco são **ISO 8601 em UTC** (`banco.utc()`), porque comparações são feitas como texto — misturar fusos já causou bug.

## Tabelas (`banco.py`)

| Tabela | Conteúdo |
|---|---|
| `jogo` | todo app conhecido (lista, DLCs, itens de bundle, biblioteca): nome, tipo, pai (DLC), capa, capa_v, análises, preço Steam (pacote base), `pacote` (subid), `fim_desconto`, `franquia`, `menor_itad`, `prioridade` (ordem na wishlist), flags `na_lista`/`possuido` |
| `dlc` | appid da DLC → pai, `classe` (historia/conteudo/cosmetico/atalho/extra/pacote), `origem` (auto/usuario) |
| `opcao` | bundles (`bundle:<id>`) e edições (`edicao:<packageid>`): preços, `desconto_bundle`, `itens` (JSON de appids), `papel` (parcial/completa/outra) |
| `jogo_opcao` | ligação jogo ↔ opção |
| `preco` | histórico: `appid, loja, preco, cheio, corte, quando, fonte (itad, itad-historico, steam, gg, calculado), url`. Só grava quando muda. Lojas especiais: `Steam (direto)`, `Completo (Steam)`, `GG.deals oficial/keyshop` |
| `oferta_atual` | snapshot das ofertas vigentes (última resposta da ITAD) com `drm_steam`, `flag` (H/N/S), `expira`. **Usar esta tabela para "preço de agora"**, nunca o último registro do histórico |
| `gg` | última leitura da GG.deals |
| `historico_importado` | jogos cujo histórico da ITAD já foi importado (`escopo='todas'`) |
| `consulta_lenta` | cache das consultas lentas da loja (`pacote`, `dlcs`; `dlcs_falha` = última falha do plano B, não conta como consultado) com data |
| `alerta` | notificações enviadas |
| `notificado` | estado por jogo para não repetir aviso (preço avisado, ativo) |
| `tenho_manual`, `silenciado` | ações do usuário no painel |
| `meta` | chave→JSON (abaixo) |

Migrações: colunas novas entram por `ALTER TABLE` tolerante em `Banco.__init__`; mudanças de dados usam `meta.esquema` (`_migrar`).

## Chaves de `meta`

`steamid`, `steamid_perfil`, `itad_ids` (cache appid→id ITAD), `lojas_itad`, `ult_steam`, `ult_itad`, `ult_gg`, `ult_biblioteca`, `ult_completa`, `ultimos_alertas` (para o painel; itens com `tipos`, `tipo_oferta`, `avisa_por`), `linha_de_base`, `tipos_ligados` (tipos de aviso da última rodada; ligar um tipo novo registra quem já estava assim sem toast), `pausado`, `pendentes` (silêncio), `avisos_fim`, `carrinho` (da Steam, via userdata), `dlcforapps_bloqueado`, `edicoes_manuais`, `esquema` (restos antigos: `ponte_vista`, `ponte_ultimo_envio` e a tabela `fila_lista`, da ponte removida na 0.16, não são mais lidos nem criados).

## `config.json` (padrões em `config.PADRAO`)

- `perfil_steam`, `pais`, `userdata_json`, `pasta_kurokami_precos`
- `lojas` (alertam), `somente_drm_steam`
- `alerta`: `tipos{selo,novo,igual,24m}` (o que avisa; padrão só `selo`), `desconto_minimo` (vale para novo, igual e 24m), `selo_corte_minimo` (Selo só a partir desse corte; padrão 0), `dias_minimos_completo`, `tolerancia_pct`, `janela_dias`/`perto` (informativos). Ignorados, ficam por compatibilidade: `raridade_minima` e `favoritos_top` (desde a 0.15), `score_minimo`, `avaliacao_minima` e `ignorar_sem_avaliacoes` (desde a 0.14)
- `keyshops`: `ativo`, `preco_maximo`, `pct_do_menor_oficial`
- `dlc`: `ignorar_cosmeticos|extras|atalhos|pacotes|gratis`
- `completo`: `padrao`, `jogos{appid:"completo"}`
- `bundles`, `notificacoes` (`ativas, max_por_rodada, melhora_minima_reais, silencio{}, termina_em_breve_horas`)
- `intervalos_minutos{itad, ggdeals, steam}`, `chamadas_lentas_por_rodada`, `verificacao_completa_dias`, `historico.importar_dias`
- `extras[]`, `painel{rede_local}`, `atualizacao{repo, verificar}`

`config.carregar()` faz merge do arquivo sobre `PADRAO`, então chaves novas não exigem migração.

## Conta Steam (seguidos e ignorados)

`conta_steam.relacao(cfg)` lê `rgFollowedApps` e `rgIgnoredApps` do `userdata.json` (cache pela data do arquivo) e nunca grava no banco. É o único leitor dessas chaves; a spec 06 (login por QR) troca só essa função.

## Segredos

Chaves (`steam`, `itad`, `ggdeals`) ficam no **Gerenciador de Credenciais** (keyring, serviço `Kurokami Radar`); variáveis `KUROKAMI_<NOME>_KEY` têm prioridade (útil em testes). Nunca gravar chave em arquivo nem em log.
