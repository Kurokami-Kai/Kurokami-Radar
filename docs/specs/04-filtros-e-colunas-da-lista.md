# Spec 04 — Filtros, colunas e "DLCs em promoção" (inspiração SteamDB)

Status: **a implementar** (depois da spec 01) · Skills: `editar-painel`, `testar-sem-rede`

## Problema
Navegar a lista de desejos com 1.000+ jogos é lento: não dá para ver de relance o que acabou de entrar em promoção ou o que está acabando, nem combinar filtros e saber quais estão ativos. A página de promoções da SteamDB resolve isso bem. A SteamDB é só inspiração de interface: nada é lido dela, e o visual continua o da loja Steam.

## Dados que já existem
`fim`/`fim_desconto`/`expira` (fim do desconto), histórico por loja (dá o início do episódio atual; a spec 01 já monta os episódios), `favorito`, `mudo`, `extra`, `base_tenho`, carrinho, faltantes da Biblioteca com preço e menor.

## Proposta
1. **Colunas Termina e Começou** na visualização em tabela da Lista de desejos ("em 5 dias", "há 2 dias"). "Começou" = início do episódio de promoção atual nas lojas marcadas (reaproveitar os episódios da spec 01). Na API, acrescentar o campo `inicio` em /api/lista.
2. **Ordenação por coluna**: clique ordena e inverte a direção; Shift+clique soma um critério. Vale para nome, corte, preço, raridade, piso, termina, começou e lançamento. Análises entram só como ordenação informativa, nunca como filtro de "vale a pena".
3. **Chips de filtros ativos** acima da lista: cada filtro aplicado (busca, faixas, estados, pílulas) vira uma pílula com ×, mais um "Limpar filtros". Os filtros aplicam na hora (sem botão "aplicar") e o estado fica salvo com `ls.set`.
4. **Filtros de 3 estados** (excluir / indiferente / exigir) para: Favorito, Silenciado, Fora da lista (extra), No carrinho e Tenho a base. Combinação sempre E.
5. **Faixas e pílulas**: preço de/até, corte mínimo da lista (independente do `desconto_minimo` de alerta), filtro por pílula de piso (novo recorde / recorde raro / igual / 24 meses), por raridade e "Selo Kurokami".
6. **Biblioteca → "DLCs em promoção"**: DLCs que eu não tenho de jogos que tenho, com desconto agora, respeitando as classes ignoradas no config (`relevantes()`). Mostrar capa, nome, jogo pai, preço, corte, pílula de piso, Termina e botão + do carrinho. ANTES de implementar, verificar no banco real de onde vem o preço atual das DLCs (oferta_atual da ITAD ou só o preço Steam) e dizer isso no resumo. Se for só Steam, mostrar "preço Steam".

## Fora desta spec
Followed / In Family / Watched, filtros por tags, sistema e recursos, cartão de hover, "Match any", faixa do evento da Steam (não há fonte para a data → registrar em docs/pendencias.md como ideia).

## Arquivos
`painel.html` (lista, biblioteca, CSS), `painel.py` (`api_lista`: `inicio`; `api_biblioteca`: DLCs em promoção), docs/api.md, README.md, docs/novidades.md.

## Aceite
- Ordenar por "Termina" coloca primeiro o que acaba antes; ordenar por "Começou" coloca primeiro o que acabou de entrar.
- Chips refletem exatamente os filtros ativos; × remove só aquele; o estado persiste ao recarregar.
- "Exigir Favorito" + "Excluir Silenciado" funciona combinado.
- "DLCs em promoção" lista só DLCs relevantes não possuídas de jogos possuídos; imprimir quantas são hoje no banco real.
- Funciona no celular (`max-width:720px`).
- Nenhum filtro de "vale a pena" depende de análise.
