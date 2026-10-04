# Spec 01 — Raridade v2, Selo Kurokami e fim da avaliação como métrica

Status: **feito em v0.14.0** (Selos e Recorde raro validados pelo dono antes de publicar) · Pedido do dono em 02–03/10/2026 · Skills: `kurokami-code`, `testar-sem-rede`, `editar-painel`

## Problema (palavras do dono, resumidas)
1. "Avaliação como métrica não vale." Os jogos já estão na lista de desejos: análise da Steam não deve decidir se uma promoção presta.
2. As etiquetas estão erradas: promoções marcadas como **Lendário** são **recorrentes** — basta olhar o histórico.
3. Falta um selo para quando o jogo está na melhor oferta da história dele: **Selo Kurokami**. Ex.: um jogo cujo desconto máximo da vida é 50%, chegando a 50%. 20% num jogo que nunca passa de 20% não é. E um jogo que fica R$ 10 todo mês, sem exceção, tem bom preço mas **não** é Selo Kurokami. *(Definição final na emenda de 04/10 — "F ou G".)*

## Diagnóstico com dados reais (banco do dono, 02/10)
| Jogo | Histórico de cortes (lojas marcadas) | Hoje | v1 disse | Deveria |
|---|---|---|---|---|
| Castle of Illusion | 75% em **55** registros desde 2021; 77% 1x; 80% 1x | 80% | Lendário (preço nunca visto) | recorrente com 5 pontos a mais → Comum/Incomum, no máximo "novo recorde por pouco" |
| Hotline Miami 2 | 85% em 73 registros, 80% em 31 | 85% | Comum | Comum (ok) |
| The Last Campfire | 90% em 26 registros | 90% | Incomum | Comum/Incomum |
| Forza Horizon 6 | máx. 20% (lançado em 2026) | 20% | — | histórico curto: sem raridade alta |

Causa: a v1 mede **preço em reais** e chama de Lendário qualquer centavo abaixo do piso. Mudanças de preço base (ex.: HLM2 R$ 24,99 → R$ 46,99) e diferenças mínimas de corte (75% → 80%) viram "nunca esteve tão barato".

## Modelo novo: dois eixos + selo

### Eixo 1 — Raridade = frequência do desconto (não do preço)
- Usar **corte (%)**, não reais (imune a mudança de preço base). Converter histórico em **episódios** de promoção: sequência de dias com corte > 0 nas lojas marcadas = 1 episódio; guardar o **maior corte** de cada episódio.
- **Tolerância de nível**: cortes até **5 pontos** abaixo do atual contam como "mesmo nível" (75% conta como episódio quando hoje é 80%).
- Janela: últimos **24 meses** (ou o histórico todo se menor). Frequência = episódios no nível ÷ anos observados.
- Níveis (calibrar com os dados; valores iniciais):
  - **Comum**: ≥ 3 episódios/ano no nível
  - **Incomum**: 1,5–3/ano
  - **Raro**: 0,75–1,5/ano
  - **Ultrarraro**: < 0,75/ano (aconteceu ≤ 1 vez em 2 anos)
  - **Lendário**: nunca atingiu esse nível (com tolerância) em ≥ 12 meses de histórico *(trocado pela regra C — ver emenda de 04/10)*
- Histórico < 6 meses → sem nível acima de **Incomum** (mostrar "histórico curto").

### Eixo 2 — Piso = quão perto do máximo da vida do jogo
- `corte_max` = maior corte já visto (lojas marcadas, todo o histórico).
- **No piso**: corte atual ≥ `corte_max` − 5 pontos **ou** preço ≤ menor preço de 24 meses (+1%).

### Selo Kurokami (badge à parte, acima de tudo)
*Definição original, substituída pela emenda "Selo = F ou G" (04/10).* Todas as condições:
1. **No piso** (eixo 2): é o melhor que esse jogo costuma chegar;
2. **Raridade ≥ Raro** (eixo 1): não é a promoção de todo mês;
3. **Histórico ≥ 12 meses**;
4. Configurável: `alerta.selo_corte_minimo` (padrão 0) para quem só quer selo a partir de X%.

Exemplos esperados: jogo cujo máximo da vida é 50% e chega a 50% 1x/ano → **Selo**. Jogo a R$ 10 todo mês (no piso, Comum) → **sem selo**. Castle of Illusion a 80% → **sem selo** (75% é Comum).

## Avaliação sai das métricas
- Remover análises do **score** e dos filtros de alerta (`avaliacao_minima`, `ignorar_sem_avaliacoes` deixam de valer; mantê-los no config por compatibilidade, ignorados).
- Novo **score** (0–100) sem análises: `corte × peso_da_raridade` (ex.: Comum 0,4 · Incomum 0,6 · Raro 0,8 · Ultrarraro 0,9 · Lendário 1,0) + bônus de piso (+10) — calibrar.
- Análises continuam **visíveis** (hover, ficha) como informação.

## Alertas
- Critério padrão: **Selo Kurokami** sempre avisa; senão `raridade ≥ alerta.raridade_minima` (padrão Raro) **e** `corte ≥ desconto_minimo`.
- Favoritos (topo da wishlist): avisam a partir de Incomum.
- Notificação: título com "SELO KUROKAMI · <jogo>" quando houver selo.

## Painel
- Pílula de raridade (níveis acima) + **badge do Selo** (visual próprio: logo Kurokami, dourado/escuro).
- Ficha do jogo: bloco "Por que essa raridade": maior corte da vida, episódios no nível nos últimos 24 meses, data da última vez.
- Filtros e ordenação: "Selo Kurokami" como filtro próprio; tirar "Melhor avaliação" do critério de "vale a pena" (pode ficar como ordenação informativa).
- Configurações: tirar "Análises positivas mínimas" e "Ignorar sem análises"; acrescentar "Selo: corte mínimo".

## Implementação sugerida
1. `analise.py`: nova `raridade_v2(linhas, corte_atual, preco_atual)` baseada em episódios; `no_piso()`; `selo_kurokami()`; novo `score()`. Manter a v1 até o fim dos testes.
2. `banco.linhas_lote` já traz `corte`; precisa da série por loja com início/fim (a v1 já monta isso — reaproveitar a varredura de eventos).
3. `avaliar()`, `painel.api_lista/api_jogo/api_carrinho`, `notificador._enviar`, `painel.html` (pílulas, filtros, ficha, config).
4. Documentar em `docs/decisoes.md` (substituir a seção de raridade) e `README.md`.

## Critérios de aceite (testar com `testar-sem-rede` no banco real)
- Castle of Illusion a 80% **não** é Lendário nem Selo.
- Hotline Miami 2 a 85% = Comum, sem selo.
- Imprimir a **distribuição** de níveis e quantos selos saem hoje; o dono valida a lista dos selos antes de publicar.
- Nenhum alerta depende de análise.

## Emenda (03/10) — Pílula de piso e "recorde raro"
Origem: estudo da página de promoções da SteamDB, usada só como inspiração. A SteamDB olha só o preço da Steam; aqui o piso é sempre entre as LOJAS MARCADAS.

- Pílula de piso, separada da pílula de raridade e do Selo. É medida em reais (eixo 2) e NUNCA alimenta a raridade (eixo 1, por frequência do corte). Usa a tolerância que já existe (≤ R$ 0,10 ou 1% = igual):
  - "Novo recorde" (azul): preço atual abaixo do menor já visto.
  - "Recorde raro" (azul-claro, variante do anterior): é novo recorde E (a última vez que o preço esteve no nível do recorde anterior foi há ≥ 18 meses OU o preço atual é ≤ 50% do recorde anterior). A regra é nossa: a SteamDB não documenta a dela.
  - "Igual ao recorde" (verde).
  - "Menor em 24 meses" (roxo): ≤ menor dos últimos 24 meses, sem ser recorde.
  - Nenhuma das anteriores: referência em cinza "menor: R$ X a -Y% (mês/ano)".
- A caixa de desconto continua verde no estilo da loja Steam. A pílula fica ao lado do preço; não recolorir a caixa.
- A definição de "no piso" do Selo não muda.
- API: em /api/lista e /api/jogo, acrescentar `piso_tipo` (novo | raro | igual | 24m | null) e `piso_ref` {preco, corte, quando}.
- Aceite extra: imprimir a distribuição de piso_tipo no banco real e os jogos com "Recorde raro", para o dono validar. Castle of Illusion a 80% continua sem Lendário e sem Selo, seja qual for a pílula.
## Emenda (04/10) — Lendário pela regra C
Verificação no banco real (22 Lendários com a regra original):
- A regra já olhava o histórico **inteiro** (não só 24 meses). O histórico importado começa em 03/10/2021 (limite da ITAD).
- Nos 22, o corte atual era de fato o maior já visto nas lojas marcadas. BRAVELY DEFAULT II, STAR OCEAN e STRANGER OF PARADISE são máximos reais (cortes subindo ano a ano; os 70% só no episódio atual).
- 10 dos 22 tinham 12–23 meses de histórico. O **ARK: Survival Evolved** era buraco nos dados: nas lojas marcadas só um brinde (2022) e um preço cheio (2023), contados como 42 meses de histórico sem nenhuma promoção.

Regra C (aprovada pelo dono):
- **Lendário** = nunca chegou ao nível no histórico inteiro **e** ≥ 24 meses de histórico **e** ≥ 1 promoção anterior nas lojas marcadas.
- 12–24 meses de histórico → no máximo **Ultrarraro**.
- Nenhuma promoção anterior nas lojas marcadas → no máximo **Incomum** (sem Selo).
- Simulação no banco de 03/10: Lendários 22 → 11, Selos 43 → 42 (sai o ARK).
- Testes sintéticos em `tools/testar_piso.py` (rodam no `checar.py`), junto com os de Recorde raro (17/19 meses desde a **última** vez no nível do recorde anterior; ≤ 50%).

Também nesta rodada: "Termina em breve" passou a respeitar `notificacoes.max_por_rodada` com resumo, e `py radar.py testar-notificacao --selo` mostra o toast de Selo.
## Emenda (04/10) — Selo = F ou G
Promessa, em linguagem simples, em todo lugar onde o Selo é explicado: **o jogo está na melhor oferta da história dele: o maior desconto ou o menor preço em muito tempo**. Sem "raro", sem "graal", sem prometer que não vai se repetir.
- **F** = Lendário (regra C). **G** = pílula Recorde raro. Em ambos, corte ≥ `alerta.selo_corte_minimo`. Raro e Ultrarraro sozinhos não ganham Selo (continuam alertando pela `raridade_minima`).
- Motivo diz qual bateu (toast, ficha e relatório): "Selo Kurokami: maior desconto da história (-85%; antes, no máximo -80%)" ou "Selo Kurokami: menor preço desde mm/aaaa" (mês/ano do início do histórico). Na API: `selo_motivo`.
- Ficha, quando houver Selo: "Nos dados de 2022–2025, em cerca de 7 de 10 casos assim o jogo não ficou mais barato nos 12 meses seguintes."
- Por quê: backtest A–H em `docs/decisoes.md` (meta fixada antes: ≥ 70% não batido em 12 meses e ≤ 3 Selos por semana normal; "F ou G" deu 70,1% e 1/semana).
- Banco de 04/10: **11 Selos** (todos F) e **38 alertas** (11 Selos, 20 Ultrarraros, 7 Raros).
- Pendente: 1ª promoção ≤ 50% do preço cheio conta como Recorde raro (ver `decisoes.md`).
