# API do painel (HTTP local)

Servidor: `painel.py` (`ThreadingHTTPServer`), porta 80 com reserva na 8787. Tudo em JSON UTF-8.

**Acesso.** Requisições de `127.0.0.1`/`::1` são sempre aceitas. De outros IPs: só com `painel.rede_local = true` e cookie `kr=<PIN>` (obtido em `POST /entrar`, 8 tentativas por 10 min). **POST** exige `Origin` igual a `http://<Host>` (proteção contra sites de fora), exceto `/api/ponte/feito` vindo do próprio PC (o Tampermonkey não manda Origin do Radar). `/api/acesso` e `/api/sair` só aceitam o próprio PC.

## Páginas

| Rota | O que é |
|---|---|
| `GET /` | redireciona para `/kurokami` |
| `GET /kurokami` | `painel.html` |
| `GET /kurokami/ponte.user.js` | userscript da ponte (Tampermonkey instala ao abrir) |
| `GET /kurokami/acao?silenciar=<appid>` | botão "Não avisar mais" das notificações (só local) |
| `GET /kurokami/acao?atualizar=1` | abre a janela de atualização (só local) |
| `POST /entrar` | formulário do PIN (form-urlencoded `pin=`) |

## GET

| Rota | Resposta (campos principais) |
|---|---|
| `/api/resumo` | `versao, na_lista, possuidos, vale_a_pena, atualizado, pausado, na_bandeja, proxima, estado, userdata_dias, atualizacao, progresso{ativo,modo,etapa,atual,total,decorrido,log[],ultima}, ult_completa, completa_dias` |
| `/api/lista` | `itens[]`: `appid, nome, tipo, capa, rpos, rcount, rotulo, lancamento, preco, cheio, corte, loja, url, piso, piso_geral, pisos{3m,6m,9m,1a,sempre}, tag, tag_texto, acima, raridade, raridade_texto, no_piso, score, keyshop, hist_keyshop, gg_url, vale, novo, motivo, base_tenho, bundles, n_dlcs, modo, extra, fim, prioridade, mudo, favorito` |
| `/api/jogo?appid=` | `jogo{}, historico{loja:[[iso,preco]]}, lojas[{loja,atual,cheio,corte,url,menor,marcada,vende}], dlcs[], dlcs_estado (só sem DLCs: `{motivo: pendente\|sem_dlcs\|falhou, quando?, fila?{atual,total}}`), caminhos[], combo, gg, modo, classes, tenho, tenho_manual, mudo, na_lista, fila, ponte_vista` |
| `/api/alertas` | último resultado de `avaliar` (`quando, itens[], novos[]`) |
| `/api/notificacoes` | `itens[]` da tabela `alerta` (200 mais recentes) |
| `/api/config` | `config, lojas_itad[], classes` |
| `/api/carrinho` | `itens[]` (com `lojas[]`, `raridade`, `em_bundle`, `fim`), `bundles[]` (preço para você, itens), `sugestoes[]` (bundles com ≥1 item do carrinho), `steam[]`, `ponte_vista, ponte_falhas[], sem_pacote[]` |
| `/api/buscar?q=` | busca na loja (nome, appid ou link) → `itens[{appid,nome,capa,preco,corte,tipo,na_lista,possuido}]` |
| `/api/biblioteca` | `jogos[]` (valor, DLCs que contam, faltantes com preço/menor, bundles), `total{hoje,cheio,menor,falta_*}`, `franquias[]` (séries), `sem_lista_dlc, sem_dados, atualizado, falta_ids` |
| `/api/acesso` | `rede_local, porta, ips[], pin, links[]` (só local) |
| `/api/ponte` | para o userscript: `carrinho[{tipo:app|bundle, appid/subid ou bundleid, nome, url}]` (só itens da Steam; busca na hora o pacote que faltar), `fila[{appid,acao}]` |

## POST

| Rota | Corpo | Efeito |
|---|---|---|
| `/api/config` | `{config:{...}}` | grava as chaves permitidas do config |
| `/api/dlc` | `{appid, classe}` | reclassifica DLC (origem `usuario`, não é sobrescrita) |
| `/api/modo` | `{appid, modo:"base"|"completo"}` | modo de alerta do jogo |
| `/api/verificar` | — | verificação rápida agora (precisa da bandeja) |
| `/api/atualizar_tudo` | — | verificação completa agora |
| `/api/pausar` | — | alterna pausa das notificações |
| `/api/carrinho` | `{itens:[{appid,loja}|{bundle}]}` | grava `dados/carrinho.json` |
| `/api/extra` | `{appid, remover?}` | monitora/para de monitorar jogo fora da wishlist (`config.extras`) |
| `/api/tenho` | `{appid, tenho}` | "já tenho" manual (tabela `tenho_manual`), tira do carrinho |
| `/api/silenciar` | `{appid, mudo}` | sem notificações para o jogo |
| `/api/lista_steam` | `{appid, acao:add|remove|cancelar}` | fila para a ponte aplicar na lista de desejos da Steam |
| `/api/ponte/feito` | `{lista:[{appid,acao,ok}], carrinho:{enviados,falhas,itens_falhos[]}}` | retorno da ponte |
| `/api/acesso` | `{rede_local?, novo_codigo?}` | liga/desliga rede local (reinicia o servidor), troca o PIN |
| `/api/atualizar_app` | — | abre a janela de atualização |
| `/api/sair` | — | fecha o Radar (usado pelo instalador .bat) |
