# Spec 07 — Promoções da Steam inteira

Status: **implementada em 08/10/2026; revisada na mesma noite com recordes e histórico (não publicada; o dono testa antes)** · Pedido do dono em 08/10/2026 ("puxar todos os jogos da Steam, não só os da lista de desejos") · Base: spec 04, item 1.6 e Etapa 1c · Skills: `kurokami-code`, `coleta-e-apis`, `banco-e-migracao`, `editar-painel`

O dono pediu e saiu ("só pare se encontrar algum problema"); as decisões abaixo foram tomadas sem ele e estão marcadas **[decidido]** para revisar.

## Problema
A aba Promoções só mostra a lista de desejos (+ monitorados). Na SteamDB dá para explorar todas as promoções da Steam (~65 mil jogos, ~108 mil itens em grande promoção).

## Dados reais (spec 04, 1.6 e 1c; conferido de novo em 08/10)
- `IStoreQueryService/Query/v1` sem chave, `sort: 2` (sem `sort` a paginação repete itens), 1.000 itens por chamada, `min_discount_percent: 1`, país BR. Em grande promoção: 108 chamadas, ~2,7 min, 107.927 itens (64.879 jogos, 35.449 DLCs). Em 08/10 (fora de promoção): 6.775 itens.
- Uma chamada traz tudo que a aba precisa: `name`, `type` (0 jogo, 4 DLC), `best_purchase_option` (`packageid`, `final_price_in_cents`, `original_price_in_cents`, `discount_pct`, `active_discounts[].discount_end_date`), `reviews.summary_filtered` (`review_count`, `percent_positive`, `review_score_label`), `release.steam_release_date`, `assets` (`asset_url_format`, `header`). ~6% dos itens vêm sem `best_purchase_option` (não compráveis): ficam fora.
- **A resposta vem em gzip se pedida:** 1,5 MB → 150 KB por página. Os 126 MB/dia da spec 04 eram sem gzip; com gzip, ~16 MB por coleta em grande promoção e ~1 MB num dia comum.
- Histórico: só os itens com desconto vêm; a volta ao preço cheio se infere pela saída da lista. Começa do zero (Selo e recordes só para a lista, que tem histórico da ITAD).

## Proposta
### Coleta (`radar/steam_inteira.py`, etapa nova no fim de `coleta.atualizar`)
- A cada **60 min** (`intervalos_minutos.steam_inteira`, muda em Configurações), no **"Verificar agora"** e na verificação completa (`meta.ult_steam_inteira`; `config.steam_inteira`, ligado por padrão). Falha só registra no log e tenta na próxima rodada. *(Revisão do dono em 08/10: 6 h era tempo demais e o "Verificar agora" precisa puxar.)*
- `rede.http_json` passa a pedir e aceitar gzip (vale para todas as fontes).
- Tabela `steam_promo`: só o retrato de agora; cada coleta **substitui** tudo, sem histórico *(revisão do dono em 08/10: basta substituir; o espaço fica do tamanho de uma coleta)*. Ver `docs/dados.md`.
- Coleta incompleta (erro no meio): não apaga quem não foi visto; só a coleta completa troca o retrato.

### Painel
- Promoções ganha **Lista de desejos | Steam inteira** no topo da barra lateral **[decidido: lembra a última escolha; na primeira vez abre em "Steam inteira" e, até a primeira coleta, mostra a lista com um aviso]**. Os filtros e a ordenação são os mesmos, no servidor; `fonte: "steam"` no `q`.
- Na Steam inteira, quem está na sua lista (ou monitorado) aparece com a linha completa (piso, "Costuma voltar", tipos de recorde); os demais vêm com o que a Steam informa (preço, corte, fim, análises, nota, lançamento). Filtros que dependem de histórico ("Mostrar só" recordes, "Costuma voltar") só acham os jogos da lista.
- Relação com o jogo funciona nos dois: na lista, monitorado, no carrinho, seguido, ignorado, já tenho. Limitação: "Tenho o jogo base" e "Silenciado" só valem para jogos da lista.
- Linha de jogo fora da lista: clicar abre a página na Steam (não há ficha sem histórico); **+** põe no carrinho do Radar e passa a monitorar (como "Adicionar jogo").
- **[decidido]** Vitrine e avisos continuam só com a lista (avisar a Steam inteira seria centenas de toasts por dia).
- Desempenho: as linhas leves ficam em memória com `__slots__` (~50 MB com 108 mil); a ordenação passa a ser por chaves estáveis (era `cmp_to_key`, lento com 100 mil). Meta: `/api/promocoes` ≤ 300 ms com 108 mil itens.

## Revisão do dono (08/10, noite)
Pedido depois de testar: (1) "demorou demais" — a Steam inteira era a última etapa da coleta e esperou 7 min atrás do catálogo da lista; (2) "não puxou nada no Selo Kurokami, nem histórico"; (3) a SteamDB mostra 40.046 e o Radar 7.355; (4) Promoções abre com DLCs; (5) o botão "Lista de desejos | Steam inteira" não tem razão de existir, o filtro "Na lista de desejos" faz isso; (6) menus no topo e títulos da vitrine clicáveis.

**Dados (medidos em 08/10):**
- **A SteamDB estava desatualizada**, não o Radar: o próprio aviso amarelo dela diz que há jogos demais na fila de atualização. BeamNG.drive, Battlefield 6 e Dungreed apareciam lá com "terminou há 5 horas" e na loja (`appdetails`) já estavam com preço cheio. A Query responde 6.905 itens com desconto (6.888 apps+DLCs; pacotes 17, bundles 0). Fica como está.
- **ITAD em lote:** `lookup/id/shop/61` (200 por chamada) dá o id ITAD de todos os 6.666 em 12 s; `games/prices/v3` com `shops=61` (200 por chamada, 14 s) traz, na oferta da Steam, `flag` (**N** = novo recorde, **H** = igual ao recorde, **S** = menor da loja) e `historyLow{all, y1, m3}` (todas as lojas da ITAD). Em 08/10: N 591, H 2.482, S 496; "perto do recorde" (marca ou preço ≤ menor de 1 ano) 4.630 itens, 2.705 jogos (393 com ≥ 500 análises).
- **Histórico** (`games/history/v2`, 1 por jogo, ~0,3 s, ~150 registros) é o que dá Selo, "Menor em 2 anos" e "Costuma voltar". **A ITAD tem cota: ~100 chamadas a cada 5 min** (429 com `Retry-After` de até 210 s, contando para baixo).

**Feito:**
- A Steam inteira roda **logo depois das listas** (etapa 1b, ~10 s + ITAD), não no fim. A marca e os menores da ITAD vêm junto, antes de gravar (o painel nunca vê o retrato sem recordes), e ficam guardados (`promo_estado`): só são pedidos de novo quando o preço muda ou passou 1 dia. Até 20 lotes (4 mil itens) por rodada, os mais avaliados primeiro (numa grande promoção, ~540 lotes estourariam a cota).
- **Histórico aos poucos** (etapa 6, no fim): 60 jogos por rodada (`steam_inteira_hist_por_rodada`), primeiro os novos recordes, jogos antes de DLCs, os mais avaliados antes; no primeiro 429 para na hora e continua na próxima rodada. Já baixado: só o que veio depois (`since`), quando o preço muda ou a cada 7 dias. Lojas = as marcadas (mudou: baixa de novo). Quem saiu da Steam inteira há 60 dias é apagado.
- **Avaliação igual à da lista** (`analise.analisar` nas lojas marcadas) para quem tem histórico; sem histórico, vale a marca da ITAD (N → Novo recorde, H → Igual ao recorde) até ele chegar. Medido na cópia: Pony Island (grátis) saiu com **Selo** ("preço caiu pela metade ou mais; o menor anterior era R$ 2,09, 10/2023").
- **[revisão: o dono tinha pedido sem histórico]** O retrato continua substituído a cada coleta; o histórico é só de quem está perto do recorde (~150 registros por jogo).
- Promoções **sempre** mostra lista + Steam inteira (o botão de fonte saiu); abre com **Tipo: Jogo** (DLC fora; quem já usava ganha o Jogo marcado uma vez).
- Topo: **Promoções ▾** (Vale a pena, Promoções, Lista de desejos), Biblioteca, **Configurações ▾** (Configurações, Notificações), **Carrinho** por último e o **avatar da Steam** no canto direito (menu: ver perfil, trocar de conta). "Lista de desejos" e os títulos da vitrine são **atalhos**: trocam os filtros por um tempo; "Promoções" volta aos filtros de antes (mexer num filtro do atalho faz dele os seus).
- Títulos da vitrine (Selo Kurokami, Novo recorde, Igual ao recorde, Menor em 2 anos) abrem Promoções com aquele tipo e os mesmos jogos da prateleira (lista + monitorados, sem os que você tem; o mesmo número do "Ver tudo").
- Barra de filtros mais compacta (como a da SteamDB) e a aba Promoções mais larga (1.240 px).

## Critérios de aceite
1. Uma coleta grava `steam_promo` com todos os itens compráveis em promoção e `meta.ult_steam_inteira`; a seguinte substitui tudo; "Verificar agora" puxa mesmo dentro do intervalo.
2. "Steam inteira" com os filtros padrão (desconto ≥ 50%, análises ≥ 5.000) lista jogos fora da lista de desejos, com preço, corte e fim certos (conferir 3 na loja).
3. Os jogos da lista aparecem uma vez só, com a linha completa.
4. `/api/promocoes` com `fonte: "steam"` responde em ≤ 300 ms (cache quente) com 108 mil itens sintéticos.
5. + num jogo fora da lista põe no carrinho e o Finalizar pedido o manda (pacote vem de `steam_promo`).
6. Desligar em Configurações para a coleta e a opção some (ou avisa) em Promoções.
