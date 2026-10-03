# Spec 01 — Raridade v2, Selo Kurokami e fim da avaliação como métrica

Status: **a implementar** · Pedido do dono em 02–03/10/2026 · Skills: `kurokami-code`, `testar-sem-rede`, `editar-painel`

## Problema (palavras do dono, resumidas)
1. "Avaliação como métrica não vale." Os jogos já estão na lista de desejos: análise da Steam não deve decidir se uma promoção presta.
2. As etiquetas estão erradas: promoções marcadas como **Lendário** são **recorrentes** — basta olhar o histórico.
3. Falta um selo para "o melhor preço que esse jogo realisticamente tem, e é raro": **Selo Kurokami**. Ex.: um jogo cujo desconto máximo da vida é 50% — 50% nele é um graal. 20% num jogo que nunca passa de 20% não é. E um jogo que fica R$ 10 todo mês, sem exceção, tem bom preço mas **não** é Selo Kurokami.

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
  - **Lendário**: nunca atingiu esse nível (com tolerância) em ≥ 12 meses de histórico
- Histórico < 6 meses → sem nível acima de **Incomum** (mostrar "histórico curto").

### Eixo 2 — Piso = quão perto do máximo da vida do jogo
- `corte_max` = maior corte já visto (lojas marcadas, todo o histórico).
- **No piso**: corte atual ≥ `corte_max` − 5 pontos **ou** preço ≤ menor preço de 24 meses (+1%).

### Selo Kurokami (badge à parte, acima de tudo)
Todas as condições:
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
