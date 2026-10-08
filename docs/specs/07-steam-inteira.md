# Spec 07 — Promoções da Steam inteira

Status: **implementada em 08/10/2026 (não publicada; o dono testa antes)** · Pedido do dono em 08/10/2026 ("puxar todos os jogos da Steam, não só os da lista de desejos") · Base: spec 04, item 1.6 e Etapa 1c · Skills: `kurokami-code`, `coleta-e-apis`, `banco-e-migracao`, `editar-painel`

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
- **[decidido]** A cada **6 h** (`meta.ult_steam_inteira`; `config.steam_inteira`, ligado por padrão, desliga em Configurações). Não roda no "Verificar agora" (pesa ~2,5 min em grande promoção); falha só registra no log e tenta na próxima rodada.
- `rede.http_json` passa a pedir e aceitar gzip (vale para todas as fontes).
- Tabela `steam_promo` (retrato atual: uma linha por appid em promoção) e `steam_hist` (só mudanças: entrou, mudou de preço, saiu → linha com o preço cheio e corte 0). Ver `docs/dados.md`.
- Coleta incompleta (erro no meio): não apaga quem não foi visto; só a coleta completa troca o retrato.

### Painel
- Promoções ganha **Lista de desejos | Steam inteira** no topo da barra lateral **[decidido: lembra a última escolha; na primeira vez abre em "Steam inteira" e, até a primeira coleta, mostra a lista com um aviso]**. Os filtros e a ordenação são os mesmos, no servidor; `fonte: "steam"` no `q`.
- Na Steam inteira, quem está na sua lista (ou monitorado) aparece com a linha completa (piso, "Costuma voltar", tipos de recorde); os demais vêm com o que a Steam informa (preço, corte, fim, análises, nota, lançamento). Filtros que dependem de histórico ("Mostrar só" recordes, "Costuma voltar") só acham os jogos da lista.
- Relação com o jogo funciona nos dois: na lista, monitorado, no carrinho, seguido, ignorado, já tenho. Limitação: "Tenho o jogo base" e "Silenciado" só valem para jogos da lista.
- Linha de jogo fora da lista: clicar abre a página na Steam (não há ficha sem histórico); **+** põe no carrinho do Radar e passa a monitorar (como "Adicionar jogo").
- **[decidido]** Vitrine e avisos continuam só com a lista (avisar a Steam inteira seria centenas de toasts por dia).
- Desempenho: as linhas leves ficam em memória com `__slots__` (~50 MB com 108 mil); a ordenação passa a ser por chaves estáveis (era `cmp_to_key`, lento com 100 mil). Meta: `/api/promocoes` ≤ 300 ms com 108 mil itens.

## Critérios de aceite
1. Uma coleta grava `steam_promo` com todos os itens compráveis em promoção e `meta.ult_steam_inteira`; a segunda, sem mudanças, não grava nada em `steam_hist`.
2. "Steam inteira" com os filtros padrão (desconto ≥ 50%, análises ≥ 5.000) lista jogos fora da lista de desejos, com preço, corte e fim certos (conferir 3 na loja).
3. Os jogos da lista aparecem uma vez só, com a linha completa.
4. `/api/promocoes` com `fonte: "steam"` responde em ≤ 300 ms (cache quente) com 108 mil itens sintéticos.
5. + num jogo fora da lista põe no carrinho e o Finalizar pedido o manda (pacote vem de `steam_promo`).
6. Desligar em Configurações para a coleta e a opção some (ou avisa) em Promoções.
