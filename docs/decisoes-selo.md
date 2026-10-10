# Decisões: Selo Kurokami, avisos e backtests

Leia antes de mexer no Selo, nos tipos de aviso ou em `tools/backtest_*.py`. Raridade e piso: `decisoes-raridade.md`.

- **Selo Kurokami = só G desde a 0.15 (04/10, spec 04).** F (Lendário, "maior desconto da história") saiu: na **escada de descontos** (o corte sobe um degrau por ano, ex.: Forza 20% → 30% → 40% → 50%) cada degrau novo vira "maior desconto da história" após 24 meses. Backtest de 04/10 (+5, corte): F 67,5%, G 84,3%. Selo só G: 47 eventos, **74,5% não ficou mais barato em 12 meses (R$)**, 89,4% não batido +5, ~0,2 aviso por semana normal (0,7 em grandes promoções). **Folga de centavos na "metade":** preço ≤ 50% do recorde anterior + R$ 0,10 ou 1% da metade (o maior), a mesma tolerância do "igual" (`analise._metade`); WRC 7 a R$ 2,39 com recorde de R$ 4,74 (Nuuvem, 07/2025; metade R$ 2,37) ficava sem Selo por R$ 0,02. O backtest não mudou (47 eventos, 74,5%); hoje 1 jogo da lista tem Selo (WRC 7). `selo_motivo`: "preço caiu pela metade ou mais (o menor anterior era R$ X, mm/aaaa)" ou "o menor preço anterior (R$ X) foi há N meses". Frase para os textos: "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade". O Selo **contém o rare deal** (G): não há opção "Recorde raro" separada; `piso_tipo == "raro"` sem promoção anterior conta como Novo recorde.
- **Avisos por tipo de recorde (0.15, spec 04).** Em "O que te avisa": Selo (ligado), Novo recorde, Igual ao recorde, Menor em 2 anos (desligados). Fora o Selo, só com corte ≥ `desconto_minimo`. Backtest de 04/10 (`tools/backtest_tipos.py`, semanas 10/2022–10/2025; métrica = **não ficou mais barato em 12 meses, em R$**, nas lojas marcadas; avisos novos por semana normal / grande promoção):

  | Tipo (desconto ≥ 50%, exceto Selo) | Eventos | Não ficou mais barato | Não batido +5 | Avisos/semana | "em X de 10" |
  |---|---|---|---|---|---|
  | Selo (só G) | 47 | 74,5% | 89,4% | 0,2 / 0,7 | 7 |
  | Novo recorde | 493 | 45,0% | 56,8% | 2,3 / 6,4 | 5 |
  | Igual ao recorde | 2.765 | 59,0% | 63,7% | 13,5 / 33,7 | 6 |
  | Menor em 2 anos | 321 | 67,6% | 75,1% | 1,8 / 3,1 | 7 |
  | base: toda promoção | 10.761 | 38,0% | 46,9% | 54,8 / 122,4 | 4 |

  Ligar um tipo não dispara em massa (resumo único). **Igual ao recorde fica desligado por padrão** (~14 avisos por semana). Tabela completa e números da Etapa 1/1b/1c em `docs/specs/04-vitrine-promocoes-e-avisos.md`.
- **Raridade só informa (0.15).** Raro/Ultrarraro sem Selo deixaram de avisar (26 dos 38 avisos de 04/10; backtest: 53,5% não batido, igual a "promoção no piso"). Os 5 nomes saíram das telas: a raridade virou a coluna **"Costuma voltar"**. "Nunca teve esse desconto" só quando o nível não aparece no histórico inteiro; se apareceu antes dos últimos 24 meses, "não teve nos últimos 2 anos" (Valdis Story: -50% hoje, -75% em 03/2024).
- **Favoritos não têm exceção de aviso (0.15).** `favoritos_top` ignorado; todos seguem as 4 caixas.
- **Filtros no servidor (0.15).** A aba Promoções pede `/api/promocoes` (filtra, conta e pagina no Hunter, sobre cache em memória) em vez de baixar a lista inteira, e a mesma tela serve para a Steam inteira (spec 07; ~108 mil itens com desconto no BR via `IStoreQueryService/Query`, sem chave, `sort` fixo). Primeira abertura: "Desconto ≥ 50%" e "Análises ≥ 5.000", como a SteamDB (618 → 205 jogos em 04/10). **08/10 (pedido do dono):** o menu aplica os filtros toda vez: Promoções = ≥ 50%, ≥ 500 análises, ✕ Tenho, só jogos; Lista de desejos = os mesmos três + ✓ Na lista (sem filtro de tipo: DLC na lista foi escolha sua).
- **Backtest do Selo** (`tools/backtest_selo.py`, banco de 04/10, 723 jogos, semanas 10/2022–10/2025, só com o histórico conhecido em cada data; cada Selo conta uma vez por episódio). **Meta fixada antes de olhar os resultados:** "não batido" (sem corte ≥ Selo + 5 em 12 meses) **≥ 70%** e **≤ 3 Selos por semana normal** (mediana).

  | Variante | Selos | Não batido +5 | +10 | Não voltou em 6m | Semana normal / grande promoção |
  |---|---|---|---|---|---|
  | A regra antiga (no piso + Raro+ + 12 meses) | 953 | 52,8% | 68,7% | 13,0% | 6 / 20 |
  | B A com ≥ 24 meses | 440 | 61,6% | 79,3% | 12,7% | 2 / 8 |
  | C B + escada parada | 134 | 67,2% | 79,9% | 23,1% | 0 / 2 |
  | D B + 1 por jogo a cada 12 meses | 213 | 65,3% | 79,8% | 16,9% | 1 / 4 |
  | E B + C + D | 120 | 69,2% | 80,8% | 21,7% | 0 / 2 |
  | F só Lendário (regra C) | 120 | 67,5% | 85,8% | 15,8% | 0 / 2,5 |
  | G Recorde raro ("rare deal" da SteamDB) | 51 | 84,3% | 90,2% | 29,4% | 0 / 1 |
  | H qualquer novo recorde em R$ | 996 | 33,9% | 48,8% | 16,2% | 10 / 25 |
  | F ou G (G sem exigir promoção anterior) | 147 | 70,1% | 86,4% | 15,0% | 1 / 3 |
  | **Selo final: F ou G, com ≥ 1 promoção anterior também na G** | 143 | **71,3%** | 87,4% | 15,4% | **1 / 3** |
  | alertas sem Selo (Raro/Ultrarraro, desconto mínimo) | 679 | 53,5% | 69,1% | 11,9% | 5 / 13,5 |
  | base: toda promoção | 10.725 | 47,0% | 64,1% | 9,4% | 91 / 211,5 |
  | base: toda promoção no piso | 8.481 | 52,1% | 69,4% | 7,6% | 71 / 178,5 |

  **Por que F ou G:** é a única que cumpre as duas metas (por 0,1 ponto, na margem de erro; empata com a E, mais complexa). F e G quase não se sobrepõem (24 casos), então somam volume sem perder acerto; a G sozinha acerta mais, mas tem só 51 casos em 3 anos. A regra antiga (A) acertava o mesmo que "toda promoção no piso". Os erros eram reais: escada de descontos e mudança de patamar (o novo máximo vira o normal). Ressalvas: usa a lista de hoje (viés de sobrevivência); semanas de grandes promoções aproximadas; G/H decididas em reais e "batido" medido em corte.
- **Recorde em reais por si só (H) acerta menos que qualquer promoção** (33,9% contra 47%): recorde por centavos logo é batido. Por isso "Novo recorde" vem **desligado** e, ligado, exige `desconto_minimo` (com ≥ 50%: 56,8% não batido +5, 45% em R$).
- **G também exige ≥ 1 promoção anterior (04/10, decisão do dono):** sem isso, a **primeira promoção** de um jogo com preço ≤ 50% do cheio virava Recorde raro (o "recorde anterior" era o preço cheio), o mesmo buraco do ARK. Eram 4 de 51 casos de G, com 25% de acerto; sem eles o Selo foi de 70,1% para 71,3%. A **pílula** continua dizendo "Recorde raro"; só o Selo não sai.
- **Régua da Steam é só informação (04/10, spec 04).** A SteamDB marca "rare deal" olhando só a Steam; o Hunter olha as lojas marcadas. Régua de 04/10 (5 rare deals da SteamDB): Ori e CrossCode dariam Selo também no Hunter (mas você já os tem e o Hunter não coleta possuídos); FINAL FANTASY XV não dá nem só com a Steam (R$ 37,50 > 50% de R$ 50,00 de 08/2026); The Escapists é outro pacote (R$ 4,59 = "+ The Walking Dead Deluxe"; sozinho custa R$ 9,49); WRC 7 perde por R$ 0,02. Na lista de hoje: 1 Selo e 8 Novos recordes só da Steam. Backtest só Steam: 55 eventos, 78,2% (Hunter: 47 e 74,5%). Decisão: as lojas marcadas decidem tudo; quando só a Steam dá Novo recorde ou Selo, a ficha mostra "Na Steam, é o menor preço já registrado. Nas suas lojas, <loja> já teve R$ X (mm/aaaa)." (`analise.regua_steam`).
- **"Termina em breve" usa o mesmo `max_por_rodada`** (carrinho primeiro, depois o que acaba antes; o resto vira "+N terminando em breve"): no fim de um evento da Steam, 36 de 44 alertas acabavam na mesma janela de 24 h.
