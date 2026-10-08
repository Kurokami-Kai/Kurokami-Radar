# API do painel (HTTP local)

Servidor: `painel.py` (`ThreadingHTTPServer`), porta 80 com reserva na 8787. Tudo em JSON UTF-8.

**Acesso.** Requisições de `127.0.0.1`/`::1` são sempre aceitas. De outros IPs: só com `painel.rede_local = true` e cookie `kr=<PIN>` (obtido em `POST /entrar`, 8 tentativas por 10 min). **POST** exige `Origin` igual a `http://<Host>` (proteção contra sites de fora). `/api/acesso` e `/api/sair` só aceitam o próprio PC. `/api/steam/*` (POST) e `/kurokami/steam/*` exigem, além disso, `Host` = `localhost`/`127.0.0.1`/`[::1]` (barra DNS rebinding) e, nos POST, `Origin` presente.

## Páginas

| Rota | O que é |
|---|---|
| `GET /` | redireciona para `/kurokami` |
| `GET /kurokami` | `painel.html` |
| `GET /kurokami/acao?silenciar=<appid>` | botão "Não avisar mais" das notificações (só local) |
| `GET /kurokami/acao?atualizar=1` | abre a janela de atualização (só local) |
| `POST /entrar` | formulário do PIN (form-urlencoded `pin=`) |
| `GET /kurokami/steam/entrar` | "Entrar pela Steam": redireciona (303) para a página de login da Steam (OpenID 2.0). **Só do próprio PC** (outro aparelho recebe 403) |
| `GET /kurokami/steam/retorno?s=…&openid.*` | volta da Steam: valida (state de uso único, endereço, assinatura, nonce, confirmação na Steam), grava só o SteamID em `config.perfil_steam` e vai para `/kurokami?steam=ok`. Erro: página 400 com mensagem curta. Só do próprio PC |

## GET

| Rota | Resposta (campos principais) |
|---|---|
| `/api/resumo` | `versao, na_lista, possuidos, vale_a_pena, atualizado, pausado, na_bandeja, proxima, estado, userdata_dias, atualizacao, progresso{ativo,modo,etapa,atual,total,decorrido,log[],ultima}, ult_completa, completa_dias` |
| `/api/lista` | do cache das linhas (ver `/api/promocoes`) · `itens[]`: `appid, nome, tipo, capa, rpos, rcount, rotulo, lancamento, preco, cheio, corte, loja, url, piso, piso_geral, pisos{3m,6m,9m,1a,sempre}, tag, tag_texto, acima, raridade, raridade_texto, no_piso, selo, selo_motivo (por que é Selo, ou null), piso_tipo (novo\|raro\|igual\|24m\|null), piso_ref{preco,corte,quando (última vez no nível do recorde, com folga de centavos),quando_preco (quando o preço do recorde em si apareceu)}, rar_info{corte_max,eps_nivel,por_ano,ultima,meses,curto,inicio}, score, keyshop, hist_keyshop, gg_url, vale, novo, motivo, base_tenho, bundles, n_dlcs, modo, extra, fim, prioridade, mudo, favorito` + desde a 0.15: `inicio` (início da promoção, ISO), `tipos[]` (selo/novo/igual/24m, não exclusivos), `tipo_oferta` (o mais importante, ou null), `volta_texto`/`volta_ordem`/`volta_dica` ("Costuma voltar"), `na_lista` (na lista da Steam; monitorado sem posição = falso), `tenho`, `no_carrinho`, `em_bundle`, `seguido`, `ignorado_steam` (de `conta_steam.relacao`), `keyshop_barata` (keyshop < 60% do preço). `vale` = avisaria agora. `raridade*`, `score` e `favorito` ficam na API mas o painel não mostra |
| `/api/promocoes?q=<JSON>` | explorador da aba Promoções, filtrado no Radar. `q`: `busca`, `relacao{campo:"exigir"\|"excluir"}` (campos `na_lista, extra, no_carrinho, seguido, ignorado_steam, mudo, tenho, base_tenho`), `qualquer_um` (os "exigir" com OU), `mostrar_so[]` (`tipo_oferta`), `tipo[]` (jogo/dlc), `outros[]` (`promo, bundle, completo, keyshop`), `preco_de/preco_ate` (centavos), `analises_de/analises_ate`, `nota_min`, `desconto_min`, `lanc_de/lanc_ate` (aaaa-mm-dd), `em_breve`, `ordem` (`[[campo,"asc"\|"desc"],...]`; campos `nome, corte, preco, volta, nota, analises, lancamento, fim, inicio`; padrão corte desc, nome asc; nulos sempre por último; desempate appid), `pagina` (a partir de 1), `por_pagina` (50, 100 ou 250). Grupos combinam com E; caixas dentro do grupo com OU; item sem o valor de uma faixa ligada fica fora. Resposta: `total, pagina, por_pagina, itens[]` (linhas como as de `/api/lista`), `contagens{mostrar_so{selo,novo,igual,24m}, tipo{jogo,dlc}}` (cada grupo contado com os outros filtros, sem o dele), `conta{tem_dados, quando}`. Campo ou valor desconhecido → **400** com `{erro}` em português. Com o cache pronto: ~3 ms no banco de 04/10 (808 linhas) |
| `/api/vitrine` | aba "Vale a pena": `selo{total, itens≤10}, novo{total, itens≤8}, igual{…}, "24m"{…}` (bloco = `tipo_oferta`, exclusivo; sem os que você tem; fora o Selo, só com corte ≥ `desconto_minimo`; corte desc, preço asc), `avisa{selo,novo,igual,24m}`, `desconto_minimo`, `na_lista` |
| `/api/jogo?appid=` | `jogo{}, historico{loja:[[iso,preco]]}, lojas[{loja,atual,cheio,corte,url,menor,marcada,vende}], dlcs[], dlcs_estado (só sem DLCs: `{motivo: pendente\|sem_dlcs\|falhou, quando?, fila?{atual,total}}`), caminhos[], combo, raridade, raridade_texto, selo, selo_motivo, no_piso, piso_tipo, piso_ref, rar_info, score, gg, modo, classes, tenho, tenho_manual, mudo, na_lista` + `tipos, tipo_oferta, volta_texto, volta_dica, fim, corte` e `regua_steam` (null, ou `{steam, radar, loja, preco, quando, texto}` quando só a Steam dá Novo recorde/Selo: a linha informativa da ficha) |
| `/api/alertas` | último resultado de `avaliar` (`quando, itens[], novos[]`) |
| `/api/notificacoes` | `itens[]` da tabela `alerta` (200 mais recentes) |
| `/api/config` | `config, lojas_itad[], classes` |
| `/api/carrinho` | `itens[]` (só a Steam: `lojas[]` tem 1 oferta; `modo`; `raridade`, `selo`, `selo_motivo`, `piso_tipo`, `piso_ref`, `tipo_oferta`, `corte`, `em_bundle`, `fim`), `bundles[]` (preço para você, itens), `sugestoes[]` (bundles com ≥1 item do carrinho), `steam[]`, `sem_pacote[]` |
| `/api/buscar?q=` | busca na loja (nome, appid ou link) → `itens[{appid,nome,capa,preco,corte,tipo,na_lista,possuido}]` |
| `/api/biblioteca` | `jogos[]` (valor, DLCs que contam, faltantes com preço/menor, bundles), `total{hoje,cheio,menor,falta_*}`, `franquias[]` (séries), `sem_lista_dlc, sem_dados, atualizado, falta_ids`, `dlcs_promo[]` (DLCs que contam, que você não tem, de jogos que você tem, com desconto agora: `appid, nome, capa, pai, pai_nome, preco, cheio, corte, loja, so_steam` (preço só do catálogo da Steam), `fim, tipo_oferta, piso_ref`) |
| `/api/acesso` | `rede_local, porta, ips[], pin, links[]` (só local) |

## POST

Todo POST bem-sucedido invalida o cache das linhas de Promoções (refeito na próxima leitura).

| Rota | Corpo | Efeito |
|---|---|---|
| `/api/config` | `{config:{...}}` | grava as chaves permitidas do config |
| `/api/dlc` | `{appid, classe}` | reclassifica DLC (origem `usuario`, não é sobrescrita) |
| `/api/modo` | `{appid, modo:"base"|"completo"}` | modo de alerta do jogo |
| `/api/verificar` | — | verificação rápida agora (precisa da bandeja) |
| `/api/atualizar_tudo` | — | verificação completa agora |
| `/api/pausar` | — | alterna pausa das notificações |
| `/api/carrinho` | `{itens:[{appid,modo}|{bundle,modo}]}` (`modo`: `conta` (padrão)\|`presente`\|`privado`; `loja` é ignorada) | grava `dados/carrinho.json` (sem repetidos) |
| `/api/extra` | `{appid, remover?}` | monitora/para de monitorar jogo fora da wishlist (`config.extras`) |
| `/api/tenho` | `{appid, tenho}` | "já tenho" manual (tabela `tenho_manual`), tira do carrinho |
| `/api/silenciar` | `{appid, mudo}` | sem notificações para o jogo |
| `/api/acesso` | `{rede_local?, novo_codigo?}` | liga/desliga rede local (reinicia o servidor), troca o PIN |
| `/api/atualizar_app` | — | abre a janela de atualização |
| `/api/steam/carrinho` | — | **só o próprio PC.** Monta o pedido para a extensão: `{ok, n, url, sem_pacote[]}`, com `url = https://store.steampowered.com/cart/#kurokami=PAIS:p<subid>[-presente\|-privado],b<bundleid>[-modo]` (sem repetidos). Descobre na hora o pacote que falta. Não fala com a conta: quem adiciona é a extensão |
| `/api/steam/extensao` | `{navegador?}` | **só o próprio PC.** Assistente da extensão: abre a pasta dela no Explorador e, com `navegador: true`, a página de extensões do navegador padrão (Edge, Chrome, Brave, Opera, Vivaldi; pelo `UserChoice` do registro). Devolve `{ok, pasta, navegador?, pagina?, aviso?}` (`aviso` quando o padrão não aceita a extensão, ex.: Firefox) |
| `/api/sair` | — | fecha o Radar (usado pelo instalador .bat) |
