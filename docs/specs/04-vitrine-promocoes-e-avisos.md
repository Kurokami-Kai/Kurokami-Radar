# Spec 04 — Vitrine, aba Promoções e avisos por tipo de recorde

Status: **feito em v0.15.0** (Etapas 1, 1b e 1c em 04/10/2026, resultados no fim; Etapa 2 implementada em 04/10/2026, não publicada) · Emenda e decisões de 04/10 incorporadas ao corpo (substitui a spec 04 anterior, "Filtros, colunas e DLCs em promoção") · Pedido do dono em 04/10/2026 · Skills: `kurokami-code`, `testar-sem-rede`, `coleta-e-apis` (Etapa 1), `editar-painel` (Etapa 2)

**Duas etapas. Faça a Etapa 1, entregue o relatório e PARE. A Etapa 2 só começa depois do ok do dono, que pode mudar números desta spec com base na Etapa 1.**

## Problema (palavras do dono, resumidas)
1. "Vale a pena" e "Lista de desejos" parecem a mesma coisa de jeitos diferentes. É confuso.
2. Os filtros de raridade são cumulativos ("Ultrarraro+" mostra também os Lendários). Na SteamDB cada caixa é uma coisa só, e dá para combinar caixas (ex.: "rare deals" + "Wished").
3. Há dois jeitos de fazer o mesmo filtro: a barra azul de atalhos ("Raro ou melhor 54") e as pílulas da lateral ("Raro+ 54").
4. O dono quer escolher **de quais tipos de recorde** recebe aviso, como as categorias da SteamDB (historical low, matching low, 2-year low, rare deal).
5. A SteamDB mostra todas as promoções da Steam (65.642 produtos no Autumn Sale 2026, BR). O dono quer isso no futuro (spec 07). Esta spec já prepara o terreno: a aba se chama "Promoções", os filtros rodam no Radar (não no navegador) e a Etapa 1 mede a viabilidade.
6. A SteamDB é só inspiração de interface: nada é lido dela, e o visual continua o da loja Steam.

## O que já existe (conferido no código em 04/10, commit ed59657)
- `analise.analisar` devolve `piso_tipo` ∈ {`novo`, `raro`, `igual`, `24m`, None}, `selo`, `selo_motivo`, `piso_ref` e `inicio` (início do episódio atual). Equivalências: `novo` = historical low; `igual` = matching low; `24m` = 2-year low; `raro` = rare deal.
- O **Selo** já contém o rare deal: Selo = F (Lendário) ou G (`piso_tipo == "raro"` com ≥ 1 promoção anterior). Por isso "Recorde raro" **não** vira uma opção separada. `piso_tipo == "raro"` sem promoção anterior conta como "Novo recorde".
- Backtest de 04/10 (`docs/decisoes.md`): Selo 143 eventos, 71,3% não batido (+5), 1 por semana normal; H "qualquer novo recorde" 33,9% (medido em **corte**). `igual` e `24m` **nunca foram medidos**. A coluna "semana normal" do backtest atual conta os jogos **com Selo ativo** na semana (estoque), não os avisos novos.
- `painel.api_lista` roda `analisar` para todos os jogos a cada chamada. O painel baixa a lista inteira e filtra no navegador.
- `steam.ler_userdata` lê `rgIgnoredApps`, mas o valor não é usado. `rgFollowedApps` não é lido.
- `notificador.processar`: um aviso por jogo (tabela `notificado`). A linha de base só existe na primeira rodada (`meta.linha_de_base`).
- Já estão em `/api/lista`: `extra` (`config.extras`), `mudo`, `base_tenho`, `favorito`, `prioridade`, `fim`, `lancamento`, `em_breve`, `rpos`, `rcount`, `tipo`.

---

## Etapa 1 — medir (relatório; o app não muda)

Regras da etapa:
- Nada em `radar/` muda e não há versão nova.
- O banco real só é lido, numa cópia temporária, como o backtest já faz.
- Resultados brutos vão para `dados/sonda/` (fora do Git).
- Só os scripts de `tools/` podem ser commitados.
- Feche o Radar antes de rodar o item 1.6.

### 1.1 Backtest por tipo
Em `tools/backtest_selo.py` (ou num `tools/backtest_tipos.py` que reaproveite as funções dele), meça 4 variantes. Cada uma é medida sozinha, como se fosse a única opção de aviso ligada, e elas **não** são exclusivas entre si:

| Variante | Condição |
|---|---|
| `selo` | `r["selo"]` |
| `novo` | `piso_tipo in ("novo", "raro")` |
| `igual` | `piso_tipo == "igual"` |
| `24m` | `piso_tipo == "24m"` |

- `novo`, `igual` e `24m` rodam duas vezes: corte ≥ 0 e corte ≥ `alerta.desconto_minimo` do config (padrão 50). `selo` roda só com `selo_corte_minimo` (0).
- Inclua a linha de base "toda promoção" com a métrica nova, para comparação.
- **Evento** = a primeira semana em que o episódio (chave `(appid, inicio)`) entra na variante, como no backtest atual.

Métricas por variante:
- **a) Eventos.**
- **b) "Não ficou mais barato em 12 meses" (R$), métrica nova.**
  - Regra: no intervalo `(ts, ts + 365 dias]`, nenhum preço nas lojas marcadas com `p < preco_evento − 10` **e** `p < preco_evento × 0,99` (centavos).
  - O resto do mesmo episódio conta.
  - Só entram eventos até `--ate` (2025-10-02), para que todos tenham 12 meses depois.
  - É esta métrica que o usuário vai ver.
- **c) As métricas existentes, para comparar:** não batido +5 e +10 (corte) e não voltou em 6 meses.
- **d) Avisos novos por semana:** eventos cuja primeira semana é aquela. Calcule a mediana nas semanas normais e nas de grande promoção (`grande_promo`). Mostre também o estoque, como hoje, numa coluna separada.
- **e) Hoje** (quantos estão na variante agora).
- **f) Texto para o usuário:** `X = round(b / 10)` e `N` = mediana dos avisos novos por semana normal, `M` = nas grandes, no formato "em X de 10 · ~N/semana (M em grandes promoções)".

**Conferência:** a variante `selo` precisa dar 143 eventos e 71,3% em +5, como em `docs/decisoes.md`. Se não der, explique a diferença antes de seguir.

### 1.2 Vitrine e avisos hoje (banco real)
- Quantos jogos cairiam em cada bloco da vitrine pela regra exclusiva da Etapa 2 (selo > novo > igual > 24m), com e sem `desconto_minimo`.
- Quantos avisos uma rodada daria hoje com só o Selo ligado, contra a regra atual. Liste os nomes que deixam de avisar (devem ser os Raro/Ultrarraro sem Selo) e os que passariam a avisar (devem ser zero).

### 1.3 userdata.json
- Se o arquivo existe e a data dele.
- Se tem as chaves `rgFollowedApps` e `rgIgnoredApps`.
- Quantos appids há em cada uma e quantos desses estão na lista de desejos.
- Só números.

### 1.4 DLCs em promoção
- Quantas DLCs relevantes (`relevantes()`), não possuídas, de jogos possuídos, estão com desconto agora.
- De onde vem o preço atual delas: quantas pela `oferta_atual` (ITAD) e quantas só pelo preço Steam de `jogo`.

### 1.5 Desempenho atual
`painel.api_lista({})` no banco real: tempo (mediana de 3 medições), número de itens e tamanho do JSON em KB.

### 1.6 Viabilidade de "Steam inteira" (BR)
Crie um script novo, `tools/teste_promocoes_steam.py`, que só lê: não grava no banco e usa `rede.py` (ritmo e backoff) com as chaves do keyring.

Fontes, nesta ordem:
1. **ITAD**, lista de ofertas atuais (`deals/v2`), país BR, só a loja Steam. Depois, uma segunda medição com todas as lojas.
2. **Steam**, `IStoreQueryService/Query`, filtrando itens com desconto, país BR, sem chave (se aceitar).
3. **Busca da loja**, `store.steampowered.com/search/results/` com `specials=1`, `cc=br` e JSON. É o último recurso: é uma página, não uma API.

Antes de cada fonte, confirme na documentação oficial o endpoint e os parâmetros. Se uma fonte não existir, exigir chave de parceiro ou recusar, registre isso e passe para a próxima.

Limites:
- No máximo 15 minutos ou 1.000 chamadas por fonte. Se o limite for atingido, extrapole.
- Uma chave por API (termos de uso).

Relatório de cada fonte:
- total de promoções (compare com as ~65 mil da SteamDB);
- chamadas, itens por chamada, tempo total, recusas/429 e tamanho baixado (MB);
- campos que vêm: appid, tipo (jogo/DLC), preço, cheio, corte, fim do desconto, menor histórico e a data dele, análises, nota, lançamento, capa;
- o que dá para calcular **sem baixar histórico**: novo recorde, igual ao recorde, menor em 24 meses, raridade, Selo.

### Entrega da Etapa 1
- A tabela 1.1, com uma linha por variante × desconto mínimo e estas colunas: eventos, não ficou mais barato (R$), não batido +5, não batido +10, não voltou em 6m, avisos novos por semana normal, avisos novos por semana grande, estoque por semana normal, hoje, texto "X de 10 · ~N/semana".
- Os números de 1.2 a 1.6.
- **PARE.**

---

## Etapa 2 — implementar (depois do ok do dono) · versão 0.15.0

### A. Avisos por tipo de recorde (`analise.avaliar`, `config`, `notificador`)
1. **Config:** em `config.PADRAO`, `alerta.tipos = {"selo": true, "novo": false, "igual": false, "24m": false}`.
2. **Tipos da oferta**, calculados sobre a oferta avaliada nas lojas marcadas:
   - `tipos` (lista, não exclusiva): `selo` se `an["selo"]`; `novo` se `piso_tipo in ("novo","raro")`; `igual`; `24m`.
   - `tipo_oferta`: o primeiro de [selo, novo, igual, 24m] presente em `tipos`, ou None. É exclusivo e é usado na vitrine, no "Mostrar só" e no título do aviso.
   - **Selo = só a regra G** (emenda 1): `piso_tipo == "raro"` com ≥ 1 promoção anterior nas lojas marcadas e corte ≥ `selo_corte_minimo`. F (Lendário) deixa de dar Selo. `piso_tipo == "raro"` sem promoção anterior conta como `novo`.
   - Na tela, `24m` se chama **"Menor em 2 anos"**.
3. **Avisa** se existe `t` em `tipos` com `alerta.tipos[t]` ligado e:
   - `t == "selo"` (o `selo_corte_minimo` já está dentro de `an["selo"]`); **ou**
   - corte ≥ `alerta.desconto_minimo`.
4. **Sem exceção para favoritos** (emenda 3): todos seguem as 4 caixas. `alerta.favoritos_top` passa a ser ignorado (fica no config por compatibilidade). O campo `favorito` pode continuar na API.
5. **Raridade não decide mais aviso.**
   - `alerta.raridade_minima` passa a ser ignorado (fica no config por compatibilidade).
   - Raro e Ultrarraro sem Selo deixam de avisar.
   - A raridade continua calculada por dentro (`rar_info`, coluna "Costuma voltar", spec 05), mas **não é mais exibida** (emenda 2).
   - Os avisos de keyshop e de modo completo não mudam.
6. **Ligar um tipo não dispara em massa.**
   - Guarde em `meta.tipos_ligados` os tipos da última rodada.
   - Quando um tipo passa de desligado para ligado, os jogos que avisariam só por causa dele entram em `notificado` sem toast. Sai um único toast: "<Tipo> ligado: N jogos já estão assim agora. Você vai receber só os próximos.", com o botão "Ver", que abre a vitrine.
   - Sem `meta.tipos_ligados` (primeira rodada da 0.15), grave os tipos atuais sem toast.
7. **Título e motivo do aviso** (use `piso_ref`; confira que, no caso `24m`, ele traz o menor de sempre, senão use o menor de sempre das lojas marcadas). O título **nunca** usa raridade (sai o "LENDÁRIO · <jogo>" / "ULTRARRARO · <jogo>" de `notificador.py`):

   | Tipo | Título | Motivo |
   |---|---|---|
   | `selo` | "SELO KUROKAMI · <jogo>" | `selo_motivo` novo: se preço ≤ 50% do menor anterior, "preço caiu pela metade ou mais (o menor anterior era R$ X, mm/aaaa)"; senão, "o menor preço anterior (R$ X) foi há N meses" |
   | `novo` | "Novo recorde · <jogo>" | "menor preço já registrado (antes R$ X em mm/aaaa)" |
   | `igual` | "Igual ao recorde · <jogo>" | "mesmo preço do menor já registrado (mm/aaaa)" |
   | `24m` | "Menor em 2 anos · <jogo>" | "menor preço em 2 anos (o menor de sempre foi R$ X em mm/aaaa)" |

8. **Ordem** da saída e do `max_por_rodada`: selo, novo, igual, 24m; dentro de cada tipo, maior corte primeiro.
9. `vale` passa a significar "avisaria agora". O "termina em breve" não muda. Os itens de `ultimos_alertas` ganham `tipos` e `tipo_oferta`.

### B. Dados da conta Steam: uma função só
- Arquivo novo `radar/conta_steam.py` com `relacao(cfg) -> {"seguidos": set[int], "ignorados": set[int], "fonte": "userdata" | None, "quando": iso | None}`.
- Ela lê `rgFollowedApps` e as chaves de `rgIgnoredApps` (str → int) do arquivo achado por `caminhos.achar_userdata`.
- Cache pela data de modificação do arquivo; nunca grava no banco; em caso de falha, devolve conjuntos vazios e `fonte = None`.
- **Nenhum outro módulo lê essas duas chaves.**
- Na docstring: "a spec 06 (login por QR) troca só esta função".

### C. Filtros no Radar (servidor)
1. **Cache das linhas.** `painel.linhas_promocoes()` monta, por jogo, os campos de `/api/lista` mais `inicio`, `tipos`, `tipo_oferta`, `na_lista`, `tenho` (`possuido` ou `tenho_manual`), `no_carrinho`, `em_bundle`, `seguido`, `ignorado_steam`, `volta_texto` e `volta_ordem` (emenda 2).
   - Fica em memória, com lock.
   - É refeito quando termina uma coleta, quando o config é gravado, nos POST de silenciar, extra, tenho, carrinho, modo e dlc, e quando o userdata.json muda de data.
2. **`GET /api/promocoes?q=<JSON url-encoded>`**
   - Campos de `q`: `busca`, `relacao{campo: "exigir"|"excluir"}`, `qualquer_um` (bool), `mostrar_so[]`, `tipo[]`, `outros[]`, `preco_de`/`preco_ate` (centavos), `analises_de`/`analises_ate`, `nota_min`, `desconto_min`, `lanc_de`/`lanc_ate` (aaaa-mm-dd), `em_breve` (bool), `ordem` ([[campo, "asc"|"desc"], ...]), `pagina` (a partir de 1), `por_pagina` (só 50, 100 ou 250; padrão 100).
   - Não há filtro de raridade (emenda 2).
   - Resposta: `{total, pagina, por_pagina, itens[], contagens{mostrar_so{selo,novo,igual,24m}, tipo{jogo,dlc}}, conta{tem_dados, quando}}`.
   - Cada contagem é calculada com todos os outros filtros aplicados, menos o do próprio grupo (como na SteamDB).
3. **Combinação dos filtros.**
   - Os grupos se combinam com E.
   - Dentro de Mostrar só, Tipo e Outros, as caixas se combinam com OU.
   - Na Relação, os "exigir" se combinam com E (ou com OU se `qualquer_um`), e os "excluir" sempre excluem.
   - Um item sem o valor de uma faixa ativa (ex.: sem data de lançamento com o filtro de lançamento ligado) fica fora.
4. **Ordenação.**
   - Campos permitidos: `nome`, `corte`, `preco`, `volta` (por `volta_ordem`: "nunca teve esse desconto" primeiro, depois "não teve nos últimos 2 anos", depois do mais raro ao mais frequente; "primeira promoção", "histórico curto" e vazio no fim, como os nulos), `nota` (rpos/rcount), `analises` (rcount), `lancamento`, `fim`, `inicio`.
   - Valores nulos ficam sempre por último; o desempate final é o appid.
   - Padrão: corte desc, depois nome asc.
5. **Validação:** campo ou valor desconhecido → 400 com mensagem em português; campos ausentes = sem filtro.
6. **Desempenho:** com o cache pronto, ≤ 300 ms no banco real. Meça e informe também o tempo da primeira montagem.
7. **`GET /api/vitrine`:** `{selo{total, itens≤10}, novo{total, itens≤8}, igual{...}, "24m"{...}, avisa{selo, novo, igual, 24m}}`, a partir do mesmo cache.
8. `/api/lista` continua existindo, com os campos novos. A vitrine e a aba Promoções deixam de usá-la.

### D. Painel

**D1. Aba "Vale a pena" = vitrine**, no padrão das prateleiras da loja Steam.
- **Topo:** carrossel "Selo Kurokami" (reaproveite o `hero`), com até 10 jogos de `tipo_oferta == "selo"` e "Ver tudo (N)". Se estiver vazio: "Nenhum jogo com Selo agora."
- **Abaixo, nesta ordem:** blocos "Novo recorde", "Igual ao recorde", "Menor em 2 anos".
  - Cada jogo aparece em um bloco só (`tipo_oferta`).
  - Os três blocos respeitam `alerta.desconto_minimo`.
  - Bloco vazio não aparece.
- **Cada bloco tem:**
  - título com 🔔 se o tipo avisa;
  - subtítulo de uma linha, só a descrição (emenda 7): Selo "O menor preço anterior foi há 1,5 ano ou mais, ou o preço caiu pela metade" · Novo recorde "Nunca esteve tão barato" · Igual ao recorde "No mesmo preço do menor já registrado" · Menor em 2 anos "No menor preço dos últimos 2 anos";
  - grade de até 8 capas (4 × 2; 2 colunas em `max-width:720px`), por corte desc e depois preço asc;
  - "Ver tudo (N)".
- **Capa:** arte, nome, caixa de preço da Steam, botão + do carrinho e, se faltar menos de 72 h, "⏳ termina em…". Sem outras pílulas.
- **"Ver tudo"** abre Promoções com Mostrar só = aquele tipo e, fora do Selo, "Desconto ≥ `desconto_minimo`". **Não** aplica o filtro de análises (emenda 4). O total exibido ali é o mesmo N.
- **Sem raridade e sem "Costuma voltar"** na vitrine.
- **Sai da aba:**
  - a lista "Todos que valem a pena";
  - as pílulas Todos/Selo/Lendário/Ultrarraro+/Raro+/Incomum+;
  - a legenda da raridade;
  - a faixa "Promoções raras da sua lista… / Ver a lista inteira".
- **Contador do topo da página:** "N na vitrine · M na lista".

**D2. Aba "Lista de desejos" passa a se chamar "Promoções"** em todos os textos visíveis (o id interno pode continuar `lista`). É um explorador que usa `/api/promocoes`.

**Filtros padrão (emenda 4):** sem estado salvo no navegador (primeira vez), a aba abre com "Desconto ≥ 50%" e "Análises ≥ 5.000" (`rcount ≥ 5000`), já como chips com ×. Com estado salvo, vale o estado salvo.

A lateral fica à direita. Em `max-width:720px`, vira um botão "Filtros" que abre um painel. Os filtros aplicam na hora (espera de 250 ms na digitação), o estado fica salvo no navegador (`ls.set`), e há os botões "Limpar filtros" (remove tudo) e "Restaurar padrão" (volta aos dois chips). De cima para baixo:

1. **Busca por nome.**
2. **"Sua relação com o jogo"**, cada linha com 3 estados: ✕ esconder / — tanto faz / ✓ só esses.

   | Linha | Campo |
   |---|---|
   | Na lista de desejos | `na_lista` |
   | Monitorado por você | `extra` |
   | No carrinho | `no_carrinho` |
   | Seguido na Steam | `seguido` |
   | Ignorado na Steam | `ignorado_steam` |
   | Silenciado | `mudo` |
   | Tenho | `tenho` |
   | Tenho o jogo base | `base_tenho` |

   - Caixa "Qualquer um": os ✓ passam a valer com OU.
   - Sem dados da conta (`conta.tem_dados` falso): Seguido e Ignorado ficam desativados, com a dica "precisa dos dados da sua conta Steam".
3. **"Mostrar só"**, combinadas com OU, cada caixa com uma bolinha na cor da sua pílula: Selo Kurokami · Novo recorde · Igual ao recorde · Menor em 2 anos (`tipo_oferta`). Cada caixa mostra a sua contagem.
4. **Listas recolhíveis**, com ponto azul no título quando há algo marcado:
   - **Tipo:** Jogo, DLC.
   - **Outros:** Só em promoção · Em bundle · Modo completo · Keyshop bem mais barata (usa o campo `keyshop` atual; a spec 05 troca a regra).
5. **Faixas:**
   - Preço de/até (R$);
   - Análises de/até;
   - Nota ≥ (0–100%, passo 5);
   - Desconto ≥ (0–100%, passo 5);
   - Lançamento de/até + "Só em breve".

   Análises e nota filtram só a tela, nunca aviso.

**Chips** acima da tabela: um por filtro ativo (ex.: "Selo Kurokami", "Desconto ≥ 50%", "Análises ≥ 5.000", "✓ No carrinho", "✕ Silenciado"). O × remove só aquele filtro.

**Tabela (padrão):**
- **Colunas:**
  - ícones (emenda 6), à esquerda da capa: carrinho em fundo amarelo se `no_carrinho`; lista em fundo verde se `na_lista`; nada nos outros casos;
  - capa;
  - nome, com o Selo e a pílula de recorde ao lado;
  - %, na caixa verde;
  - Costuma voltar (`volta_texto`; dica ao passar o mouse ou tocar: "Nos últimos 2 anos: N vezes com -Y% ou mais (última em mm/aaaa) · maior desconto que já teve: -Z%");
  - Preço;
  - Análises (%, com a cor de `revClass`);
  - Lançamento;
  - Termina ("em 5 dias"; vazio se não houver data);
  - Começou ("há 2 dias");
  - botão + do carrinho.
- **Ordenação:** clique ordena e inverte; Shift+clique soma critérios. A seta mostra a direção e o número mostra a ordem dos critérios.
- **Visualização em Grade:** usa um seletor com os mesmos critérios.
- **Itens por página** (emenda 5): seletor 50 / 100 (padrão) / 250, com a escolha salva; paginação numerada no fim da tabela. Sem "Mostrar mais".
- **No celular:** a tabela rola na horizontal dentro do próprio contêiner, sem a página rolar de lado.

**Sai da aba:**
- a barra azul de atalhos;
- as pílulas cumulativas de raridade, o filtro, a coluna e a ordenação por raridade (emenda 2);
- "Restringir por preço", "Desconto mínimo", "Análises de usuários" e "Restringir por";
- as visualizações em linhas e compacta;
- o seletor "Ordenar por".

**D3. Ficha:**
- mostrar "Termina em" sempre que houver data, e não só abaixo de 72 h;
- o bloco "Por que <raridade>" vira "Costuma voltar: <texto>", com a linha da dica embaixo; o bloco do Selo continua acima dele, quando houver (emenda 2);
- a frase "em cerca de 7 de 10 casos…" usa o número da Etapa 1b, na métrica em R$ (ver resultado da 1b);
- a frase de referência do Selo passa a ser "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade".
- **linha informativa da régua da Steam** (decisão final, abaixo): quando o jogo é Novo recorde ou Selo só pela Steam e não pelas lojas marcadas, "Na Steam, é o menor preço já registrado. Nas suas lojas, <loja> já teve R$ X (mm/aaaa)." Sem aviso e sem filtro; vem de `analise.regua_steam` (campo `regua_steam` de `/api/jogo`).

O resto da ficha é da spec 05.

**D4. Configurações:** o bloco "O que vale a pena" passa a se chamar **"O que te avisa"**.
- **4 caixas** (Selo Kurokami, Novo recorde, Igual ao recorde, Menor em 2 anos); só o Selo vem ligado.
  - Cada caixa tem uma linha fixa: a descrição da emenda 7 + " · ~N avisos por semana (M em grandes promoções)", com a **média** de avisos novos por semana da Etapa 1b (`desconto_minimo` padrão; uma casa decimal quando < 1). As 4 frases prontas estão no resultado da Etapa 1b.
  - O "em X de 10" fica só em `docs/decisoes.md`, com a data do backtest.
- **"Desconto mínimo (%)":** com a dica "vale para Novo recorde, Igual e Menor em 2 anos".
- **"Selo Kurokami: desconto mínimo (%)":** fica como está.
- **Saem:** "Avisar a partir de", a dica do Score e o campo de favoritos (emenda 3). O resto da aba é da spec 05.

**D5. Biblioteca → "DLCs em promoção"**
- **O que entra:** DLCs relevantes (`relevantes()`) que o usuário não tem, de jogos que ele tem, com desconto agora.
- **O que mostra:** capa, nome, jogo pai, preço, corte, pílula de recorde, Termina e botão + do carrinho.
- **Preço:** se o preço vier só da Steam (Etapa 1.4), escreva "preço Steam".

### E. Docs
- `docs/api.md`: `/api/promocoes`, `/api/vitrine` e os campos novos de `/api/lista`.
- `docs/dados.md`: `alerta.tipos`, `meta.tipos_ligados`, e `raridade_minima` e `favoritos_top` ignorados.
- `docs/arquitetura.md`: a regra de aviso, o Selo só G, a coluna "Costuma voltar", o cache das linhas e o `conta_steam`.
- `docs/decisoes.md`:
  - avisos por tipo, com a tabela da Etapa 1;
  - Raro/Ultrarraro sem Selo deixam de avisar;
  - o Selo passa a ser só o rare deal (G): F sai por causa da escada de descontos (F 67,5% × G 84,3% em +5, backtest de 04/10) e os números da Etapa 1b;
  - raridade sai das telas (vira "Costuma voltar") e favoritos não têm mais exceção de aviso;
  - a frase de referência do Selo: "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade";
  - filtros no servidor, pensando na Steam inteira.
- `docs/pendencias.md`: marcar como resolvido o item "Decidir se Raro/Ultrarraro sem Selo continuam alertando".
- `README.md` e a seção `## 0.15.0` de `docs/novidades.md`, em linguagem de usuário (avisar que os Selos de hoje, todos do tipo F, deixam de ser Selo; a frase nova do Selo; raridade virou "Costuma voltar").
- `tools/testar_piso.py`: casos "maior desconto da história sem recorde raro → sem Selo", "escada 40% → 50% com 30 meses de histórico → sem Selo", "recorde raro com promoção anterior → Selo".
- `tools/backtest_selo.py`: a variante "Selo" passa a ser G com ≥ 1 promoção anterior.
- Ao terminar, rode `py tools/gerar_referencia.py`.

## Emenda (04/10) — decisões do dono depois da Etapa 1

O Radar responde duas perguntas separadas:
- **"Está barato agora?"** — 4 tipos de preço, em reais. Só eles decidem aviso.
- **"Essa promoção volta sempre?"** — a coluna "Costuma voltar". Só informa.

### 1. Selo Kurokami = só o rare deal (G)
- **Selo** = `piso_tipo == "raro"` **e** ≥ 1 promoção anterior nas lojas marcadas **e** corte ≥ `alerta.selo_corte_minimo`.
  - É a regra G atual, sem mudar nada: preço abaixo do menor registrado antes do episódio atual (diferença > R$ 0,10 e > 1%), **e** (o preço esteve no nível desse recorde pela última vez há ≥ 18 meses, **ou** preço ≤ 50% dele).
- **F (Lendário / maior desconto da história) deixa de dar Selo.**
- **Motivo:** na escada de descontos (o corte sobe de degrau a cada ano, ex.: Forza 20% → 30% → 40% → 50%), cada degrau novo vira "maior desconto da história" depois de 24 meses de histórico. No backtest de 04/10, F acertou 67,5% e G 84,3% (+5, corte). Registre isso em `docs/decisoes.md`.
- **`selo_motivo`** diz qual condição bateu; se as duas baterem, use a primeira:
  - ≤ 50%: "preço caiu pela metade ou mais (o menor anterior era R$ X, mm/aaaa)";
  - senão: "o menor preço anterior (R$ X) foi há N meses".
- **Frase de referência para os textos do usuário:** "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade". Ela substitui "o maior desconto ou o menor preço em muito tempo" no README, na ficha e nos docs.
- **Ficha:** a frase "em cerca de 7 de 10 casos…" passa a usar o número da Etapa 1b, na métrica em R$.
- **Na Etapa 2:**
  - mude `analise.py`;
  - em `tools/testar_piso.py`, acrescente estes casos:
    - maior desconto da história sem recorde raro → sem Selo;
    - escada 40% → 50% com 30 meses de histórico → sem Selo;
    - recorde raro com promoção anterior → Selo;
  - a variante "Selo" do `tools/backtest_selo.py` passa a ser G com ≥ 1 promoção anterior;
  - atualize `arquitetura.md`, o README e `novidades.md` (avisar que os Selos de hoje, todos do tipo F, deixam de ser Selo).
- `tipos`/`tipo_oferta` (A.2) não mudam: `selo` se `an["selo"]`; `piso_tipo == "raro"` sem promoção anterior conta como `novo`.

### 2. Os 5 níveis de raridade saem das telas → coluna "Costuma voltar"
- **Saem de todas as telas e textos do usuário:** os nomes Comum/Incomum/Raro/Ultrarraro/Lendário, as pílulas coloridas, a legenda, o filtro "Raridade" (D2), a coluna "Raridade" e a ordenação por raridade. Isso vale para Promoções, vitrine, ficha, carrinho, biblioteca, notificações e Configurações.
- **Notificação:** o título deixa de usar raridade (sai o "LENDÁRIO · <jogo>" / "ULTRARRARO · <jogo>" de `notificador.py`). O título segue a tabela de A.7.
- **Por dentro, nada muda no cálculo:** `analisar` continua calculando nível, episódios e `rar_info` (usados pela coluna e pela spec 05). Os campos `raridade`/`raridade_texto` podem continuar na API, mas o painel não os mostra. O `score` fica só interno.
- **Campos novos** em `/api/lista` e `/api/promocoes`: `volta_texto` (string ou null) e `volta_ordem` (número para ordenar).
- **Valor da coluna** (só com corte > 0; sem promoção = vazio):

  | Situação | Texto |
  |---|---|
  | `rar_info.curto` (histórico < 6 meses) | "histórico curto" |
  | nenhuma promoção anterior nas lojas marcadas | "primeira promoção" |
  | nenhum episódio no histórico **inteiro** (desde o 1º registro nas lojas marcadas) com corte ≥ atual − 5 | "nunca teve esse desconto" |
  | teve, mas só antes dos últimos 24 meses (`eps_nivel == 0`) | "não teve nos últimos 2 anos" |
  | X < 1,5 (X = 12 / `por_ano` meses) | "todo mês" |
  | 1,5 ≤ X < 10,5 | "a cada ~N meses" (N = round(X)) |
  | 10,5 ≤ X < 18 | "1 vez por ano" |
  | X ≥ 18 | "1 vez em 2 anos" |

- **Ordenação (`volta_ordem`):** "nunca teve esse desconto" primeiro, depois "não teve nos últimos 2 anos", depois do mais raro ao mais frequente (menor `por_ano` primeiro), "todo mês" por último. "Primeira promoção", "histórico curto" e vazio ficam sempre no fim, como os nulos.
- **Dica ao passar o mouse** (tocar, no celular): "Nos últimos 2 anos: N vezes com -Y% ou mais (última em mm/aaaa) · maior desconto que já teve: -Z%". Y = corte atual − 5; N = `eps_nivel`; Z = `corte_max`. Singular quando for 1: "1 vez", "1 mês" (vale para a dica e para "a cada ~N meses").
- **Ficha (D3):** o bloco "Por que <raridade>" vira "Costuma voltar: <texto>", com a mesma linha da dica embaixo. O bloco do Selo continua acima dele, quando houver.
- **Onde aparece:** na tabela de Promoções (coluna "Costuma voltar", entre "%" e "Preço") e na ficha. Na vitrine não aparece.

### 3. Favoritos saem
- Sai a regra A.4: não há mais exceção de aviso para favoritos. Todos seguem as 4 caixas.
- `alerta.favoritos_top` passa a ser ignorado (fica no config por compatibilidade), assim como `alerta.raridade_minima`.
- Saem o campo de favoritos das Configurações (D4), a linha "Favorito" da relação com o jogo (D2) e o chip correspondente. O campo `favorito` pode continuar na API.
- No Aceite 3, troque o caso do favorito por: "um jogo com `piso_tipo == "24m"` e corte < `desconto_minimo` não avisa".

### 4. Filtros padrão ao abrir Promoções (como a SteamDB)
- **Sem estado salvo no navegador** (primeira vez), a aba abre com "Desconto ≥ 50%" e "Análises ≥ 5.000" (`rcount ≥ 5000`), já como chips com ×.
- **Com estado salvo,** vale o estado salvo.
- **Botões:** "Limpar filtros" remove tudo; um botão novo, "Restaurar padrão", volta aos dois chips.
- **"Ver tudo" da vitrine** abre com Mostrar só = aquele tipo e, fora do Selo, "Desconto ≥ `desconto_minimo`". **Não** aplica o filtro de análises, para o total bater com o N do bloco.

### 5. Itens por página
- Seletor com 50, 100 (padrão) e 250; a escolha fica salva.
- Paginação numerada no fim da tabela; o "Mostrar mais" sai.
- Em `/api/promocoes`, `por_pagina` aceita só 50, 100 ou 250.
- As `contagens` de C.2 ficam só com `mostrar_so` e `tipo` (a de raridade sai).

### 6. Ícones na linha (como a SteamDB)
À esquerda da capa, na tabela:
- ícone de carrinho em fundo amarelo se `no_carrinho`;
- ícone de lista em fundo verde se `na_lista`;
- nada nos outros casos.

### 7. Textos das 4 caixas de aviso (D4) e dos blocos da vitrine (D1)
Só a descrição e a quantidade de avisos. O "em X de 10" fica só em `docs/decisoes.md`.

| Caixa / bloco | Descrição |
|---|---|
| Selo Kurokami | "O menor preço anterior foi há 1,5 ano ou mais, ou o preço caiu pela metade" |
| Novo recorde | "Nunca esteve tão barato" |
| Igual ao recorde | "No mesmo preço do menor já registrado" |
| Menor em 2 anos | "No menor preço dos últimos 2 anos" |

- **Nas Configurações**, depois da descrição: " · ~N avisos por semana (M em grandes promoções)". Use a **média** de avisos novos por semana (não a mediana), com o `desconto_minimo` padrão, e uma casa decimal quando for < 1.
- **Na vitrine**, o subtítulo do bloco é só a descrição.
- O tipo `24m` passa a ser exibido como "Menor em 2 anos" em todos os textos do usuário.
- Só o Selo vem ligado. "Igual ao recorde" continua desligado por padrão (decisão de 04/10, depois da 1b: ~14 avisos por semana).

### Aceite (trocas)
- **Aceite 2:** com só o Selo ligado, uma rodada no banco de hoje avisa só jogos com Selo G (imprima quantos e quais). Não avisa ninguém por raridade nem por favorito.
- **Aceite 6:** sai o caso "marcar só Ultrarraro". Entram estes:
  - ordenar por "Costuma voltar" põe "nunca teve esse desconto" primeiro, depois "não teve nos últimos 2 anos", e "histórico curto", "primeira promoção" e vazios por último;
  - nenhuma tela mostra Comum/Incomum/Raro/Ultrarraro/Lendário (`grep` no `painel.html` e no `notificador.py`).

### Etapa 1b — medir e parar
1. Rode `tools/backtest_tipos.py` com a variante `selo` = G + ≥ 1 promoção anterior: eventos, não ficou mais barato (R$), não batido +5/+10, não voltou em 6m, **média** de avisos novos por semana normal/grande, hoje.
2. Reimprima a média de avisos novos por semana de `novo`, `igual` e `24m` com o `desconto_minimo` padrão.
3. No banco real de hoje:
   - quantos jogos da lista estão em promoção;
   - quantos somem com os filtros padrão (corte < 50 ou `rcount` < 5000);
   - quantos jogos com corte ≥ 50 têm `rcount` < 5000.
4. Distribuição da coluna "Costuma voltar" hoje entre os jogos em promoção (quantos em cada texto) e 3 exemplos de cada.
5. Monte as 4 frases finais do item 7 com os números.
6. Registre tudo na spec e **PARE**.

## Ajuste antes de publicar (04/10): folga de centavos na "metade" do Selo
- A condição "preço ≤ 50% do recorde anterior" ganha a folga do "igual": + R$ 0,10 ou 1% da metade (o que for maior) (`analise._metade`). Vale também na régua da Steam (`regua_steam` usa `analisar`).
- Caso real: WRC 7 a R$ 2,39 com recorde de R$ 4,74 (Nuuvem, 07/2025; metade R$ 2,37) agora ganha Selo.
- Backtest (`tools/backtest_tipos.py`, variante `selo`): 47 eventos, 74,5% não ficou mais barato (R$), média 0,2 / 0,7 aviso por semana normal / grande; hoje 1 jogo da lista com Selo (WRC 7). Casos em `tools/testar_piso.py`.

## Decisão final (04/10, depois da Etapa 1c)
- **A régua das lojas marcadas continua decidindo tudo** (avisos, vitrine, filtros). A régua só da Steam ("Steam (direto)" + Steam da ITAD) vira **uma linha informativa na ficha**, sem aviso e sem filtro.
- **Quando aparece:** o jogo é Novo recorde ou Selo pela régua só da Steam e **não** é pela régua das lojas marcadas (ou é um tipo menor: Selo na Steam, Novo recorde nas marcadas).
- **Texto:** "Na Steam, é o menor preço já registrado. Nas suas lojas, <loja> já teve R$ X (mm/aaaa)." <loja>, R$ X e a data vêm do registro das lojas marcadas que impediu (o último com o menor preço anterior).
- **Código:** `analise.regua_steam()` (e `analise.menor_anterior()`); `tools/regua_steam.py` usa a mesma função.
- **Números da Etapa 1c (lista de hoje):** 1 Selo da Steam (WRC 7: "Nas suas lojas, Nuuvem já teve R$ 4,74 (07/2025).") e 8 Novos recordes da Steam que não são do Radar (ex.: Street Fighter 6: "Nuuvem já teve R$ 68,99 (08/2026)"). Backtest só Steam: Selo 55 eventos e 78,2% não ficou mais barato, contra 47 e 74,5% do Radar.

## Resultado da Etapa 1 (04/10/2026, banco instalado: 726 jogos; lojas GreenManGaming, Nuuvem, Steam)

### 1.1 Backtest por tipo (`py tools/backtest_tipos.py`; semanas 10/2022–10/2025)
Conferência: `selo` = **143 eventos / 71,3%** em +5, igual a `decisoes.md`. "ev. qq." = episódios que entram na variante em qualquer semana (não só na primeira), para comparar.

| Variante | Eventos (ev. qq.) | Não ficou mais barato (R$) | Não batido +5 | +10 | Não voltou 6m | Novos/sem. normal (média) | Novos/sem. grande (média) | Estoque/sem. normal | Hoje | Texto |
|---|---|---|---|---|---|---|---|---|---|---|
| selo | 143 (161) | 60,1% | 71,3% | 87,4% | 15,4% | 0 (0,6) | 0 (2) | 1 | 11 | em 6 de 10 · ~0/semana (0 em grandes) |
| novo ≥ 0 | 997 (1.074) | 28,0% | 34,0% | 48,8% | 16,1% | 4 (4,7) | 9 (12,9) | 10 | 77 | em 3 de 10 · ~4/semana (9) |
| novo ≥ 50 | 493 (541) | 45,0% | 56,8% | 72,2% | 11,0% | 2 (2,3) | 4 (6,4) | 3 | 29 | em 5 de 10 · ~2/semana (4) |
| igual ≥ 0 | 3.713 (3.902) | 50,9% | 53,5% | 66,8% | 7,8% | 14 (17,9) | 45,5 (46) | 27 | 204 | em 5 de 10 · ~14/semana (45,5) |
| igual ≥ 50 | 2.765 (2.906) | 59,0% | 63,7% | 77,6% | 5,5% | 10 (13,5) | 32 (33,7) | 20 | 137 | em 6 de 10 · ~10/semana (32) |
| 24m ≥ 0 | 384 (402) | 62,5% | 69,5% | 82,6% | 5,5% | 0 (2,1) | 0 (3,8) | 1 | 66 | em 6 de 10 · ~0/semana (0) |
| 24m ≥ 50 | 321 (338) | 67,6% | 75,1% | 85,4% | 5,3% | 0 (1,8) | 0 (3,1) | 1 | 54 | em 7 de 10 · ~0/semana (0) |
| base: toda promoção | 10.761 | 38,0% | 46,9% | 64,0% | 9,5% | 47 (54,8) | 111 (122,4) | 91 | 605 | em 4 de 10 · ~47/semana (111) |

Para decidir: a mediana de avisos novos dá 0 em Selo e 24m (os eventos se concentram em poucas semanas); a média descreve melhor o volume ("~0,6/semana"). "Não ficou mais barato" em R$ é mais exigente que "não batido +5" em corte (Selo 60% contra 71%).

### 1.2 Vitrine e avisos hoje (`py tools/medir_spec04.py`)
- Vitrine (regra exclusiva selo > novo > igual > 24m): sem desconto mínimo **selo 11 · novo 65 · igual 212 · 24m 66**; com desconto ≥ 50% **selo 11 · novo 18 · igual 137 · 24m 54**.
- Avisos de uma rodada: regra atual **38**; só Selo ligado **13** (todos de lojas oficiais; keyshop e completo 0 nos dois).
- Deixam de avisar 26, todos Raro/Ultrarraro sem Selo.
- Passa a avisar 1: Coffee Talk (favorito, Comum, -50%). É efeito da regra A.4 (favorito avisa em qualquer tipo); hoje o favorito precisa de Incomum.

### 1.3 userdata.json
Não existe em nenhum caminho procurado (pasta de dados, pasta do programa, `userdata_json`, `pasta_kurokami_precos` vazios). Sem números de seguidos/ignorados. Obs.: a lista oficial de métodos públicos da Steam traz `IStoreService/GetGamesFollowed` (para a spec 06).

### 1.4 DLCs em promoção
2.159 DLCs relevantes não possuídas de jogos possuídos; **1.184 com desconto agora** (todas com fim em 08/10: promoção de outono). Preço: **10 pela `oferta_atual` (ITAD)** e **1.174 só pelo preço Steam de `jogo`**.

### 1.5 Desempenho atual
`painel.api_lista({})`: mediana **0,54 s** (0,54 / 0,54 / 0,54), **808 itens**, **1.014 KB** de JSON.

### 1.6 "Steam inteira" no BR (`py tools/teste_promocoes_steam.py`)
| Fonte | Total | Chamadas | Itens/chamada | Tempo | 429 | MB |
|---|---|---|---|---|---|---|
| ITAD `deals/v2`, só Steam | desconhecido: parou no limite de 15 min com 66.000 lidos e `hasMore` verdadeiro (18.368 jogos, 18.664 DLCs, 24.855 pacotes) | 333 | 198 | 15 min | 3 | 84 |
| ITAD `lookup/shop/61/id/v1` (appids) | 33.000 ids → 19.794 appids, depois uma falha | 172 | 192 | 7 min | 7 | 2 |
| ITAD `deals/v2`, todas as lojas | desconhecido: 55.600 lidos em 15 min (Steam é a melhor oferta em 95%) | 283 | 197 | 15 min | 5 | 71 |
| **Steam `IStoreQueryService/Query`, sem chave** | **107.927** (64.879 jogos, 35.449 DLCs, 7.599 de outros tipos: 11, 6, 2) | **108** | 1.000 | **2,7 min** | 0 | 126 |
| Busca da loja (`specials=1`) | 99.438 informados; bloqueada depois de 14.600 (156 chamadas em 5 min) | 156 | 94 | 5 min | 10 | 35 |

- Os 64.879 jogos da Steam batem com as ~65 mil da SteamDB. Todos os appids da busca e 99,8% dos mapeados da ITAD estão na consulta da Steam.
- **Pegadinha:** a `Query` sem `sort` muda a ordem entre chamadas e a paginação repete itens (só 70.000 distintos em 107.927). Com `sort: 2`, os 107.927 são distintos (1 e 13 também dão ordem estável).
- A `Query` não tem página oficial da Valve (só a referência não oficial de xpaw) e não aparece na lista pública de métodos, mas respondeu sem chave.

Campos por fonte:

| Campo | ITAD deals | Steam Query | Busca |
|---|---|---|---|
| appid | não (precisa do lookup, ~1 chamada por 200) | sim | sim (pacote vem como lista) |
| tipo jogo/DLC | sim (game/dlc/package) | sim | não (só App/Sub) |
| preço, cheio, corte | sim | sim (`best_purchase_option`) | só no HTML |
| fim do desconto | sim (`expiry`) | sim (`discount_end_date`) | não |
| menor histórico | sim (`historyLow`, `historyLow_1y`, `historyLow_3m`), **sem data** | não | não |
| análises e nota | não | sim (`reviews`) | só no HTML |
| lançamento | não | sim | só no texto |
| capa | sim (`assets`) | sim (`assets`, se pedir) | sim |

O que dá para calcular **sem baixar histórico**:
- **ITAD:** novo recorde ≈ `flag` N (14.541 de 66.000) e igual ao recorde ≈ `flag` H (22.294), mas é o recorde da ITAD (todas as lojas, desde sempre), não o das lojas marcadas. Dá também "menor em 12 meses" (`historyLow_1y`), mas não em 24. Raridade e Selo não (precisam dos episódios).
- **Steam:** nada disso (só o preço de agora).
- **Busca:** nada disso.

## Resultado da Etapa 1b (04/10/2026, mesmo banco)

### 1. Selo = só G (`py tools/backtest_tipos.py`; G com ≥ 1 promoção anterior)
| Variante | Eventos (ev. qq.) | Não ficou mais barato (R$) | Não batido +5 | +10 | Não voltou 6m | Média de avisos novos/sem. normal / grande | Hoje |
|---|---|---|---|---|---|---|---|
| **selo (só G)** | **47** (56) | **74,5%** | **89,4%** | 93,6% | 31,9% | **0,2 / 0,7** | **0** |
| selo antigo (F ou G), para comparar | 143 (161) | 60,1% | 71,3% | 87,4% | 15,4% | 0,6 / 2 | 11 |

- Confere com o `backtest_selo.py`: a G tinha 51 eventos, e 4 deles não tinham promoção anterior.
- **Hoje não há nenhum Selo G.** Os 11 Selos de hoje são todos F e somem; o carrossel da vitrine abriria vazio ("Nenhum jogo com Selo agora.") e o Aceite 2 imprimiria 0 avisos.
- Frase da ficha: "em cerca de **7** de 10 casos" (74,5%, métrica em R$).

### 2. Média de avisos novos por semana (desconto ≥ 50%)
| Tipo | Semana normal | Grande promoção |
|---|---|---|
| novo | 2,3 | 6,4 |
| igual | 13,5 | 33,7 |
| 24m | 1,8 | 3,1 |

### 3. Filtros padrão de Promoções (banco real, jogos da lista em promoção que você não tem)
- Em promoção: **618**.
- Somem com os filtros padrão (corte < 50 ou < 5.000 análises): **413**. Ficam **205**.
- Com corte ≥ 50 e < 5.000 análises: **197**. Quase todo o corte vem das análises.

### 4. Coluna "Costuma voltar" hoje (618 jogos em promoção; `py tools/medir_spec04.py`)
| Texto | Jogos | Exemplos |
|---|---|---|
| a cada ~2 meses | 162 | Anno 1503 History Edition (-50%), Dragon Age Inquisition (-75%), Nelke & the Legendary Alchemists (-77%) |
| todo mês | 149 | Balatro (-20%), Zombie Army 4 (-90%), Tales of Xillia Remastered (-25%) |
| a cada ~3 meses | 79 | Mortal Kombat: Legacy Kollection (-50%), Team Fortress Classic (-80%), RoboCop: Rogue City (-90%) |
| histórico curto | 71 | Rubinite (-20%), Counter-Strike (-80%), Assassin's Creed Black Flag Resynced (-10%) |
| a cada ~5 meses | 34 | The Alters (-55%), Rustil (-40%), Battlefield 6 (-50%) |
| nunca teve esse desconto | 32 | Valdis Story (-50%), BlazBlue Entropy Effect (-47%), FANTASIAN Neo Dimension (-60%) |
| a cada ~4 meses | 32 | Hellblade II (-75%), Atelier Ryza DX (-35%), Return of the Obra Dinn (-33%) |
| a cada ~6 meses | 21 | Atelier Yumia (-50%), Farthest Frontier (-50%), WitchSpring R (-50%) |
| a cada ~8 meses | 14 | Labyrinth of Touhou Tri (-30%), TEVI (-50%), Prince of Persia The Lost Crown (-70%) |
| 1 vez por ano | 9 | The Rogue Prince of Persia (-70%), WITCH ON THE HOLY NIGHT (-50%), Escape from Duckov (-30%) |
| 1 vez em 2 anos | 6 | First Cut: Samurai Duel (-50%), Sniper Elite: Resistance (-60%), Hi-Fi RUSH (-55%) |
| a cada ~10 meses | 4 | Mega Man Star Force Legacy Collection (-25%), NINJA GAIDEN 2 Black (-60%), LEGO Batman (-30%) |
| primeira promoção | 3 | Avatar Legends (-20%), The Adventures of Elliot (-29%), ARK: Survival Evolved (-34%) |
| a cada ~9 meses | 1 | RAIDOU Remastered (-45%) |
| a cada ~7 meses | 1 | Esoteric Ebb (-34%) |

Exemplo de dica: "Nos últimos 2 anos: 14 vezes com -70% ou mais (última em 09/2026) · maior desconto que já teve: -90%" (Dragon Age Inquisition).

Decidido em 04/10 (aplicado na emenda 2): "nunca teve esse desconto" só sem episódio no nível no histórico inteiro; senão "não teve nos últimos 2 anos"; singular nas dicas; "Igual ao recorde" desligado por padrão. O que motivou:
- **"nunca teve esse desconto" nem sempre é verdade:** `eps_nivel` conta só os últimos 24 meses. Em 5 dos 32 casos o jogo já teve esse nível antes disso. Exemplo: Valdis Story está a -50%, já teve -75% e esteve nesse nível pela última vez em 03/2024. Sugestão: usar "nunca teve esse desconto" só quando não há episódio no nível em todo o histórico (`ultima` vazio); senão, "não teve nos últimos 2 anos".
- A dica precisa do singular: "1 vez", não "1 vezes".

### 5. As 4 frases finais (Configurações; média, desconto ≥ 50%)
- **Selo Kurokami:** "O menor preço anterior foi há 1,5 ano ou mais, ou o preço caiu pela metade · ~0,2 avisos por semana (0,7 em grandes promoções)"
- **Novo recorde:** "Nunca esteve tão barato · ~2 avisos por semana (6 em grandes promoções)"
- **Igual ao recorde:** "No mesmo preço do menor já registrado · ~14 avisos por semana (34 em grandes promoções)"
- **Menor em 2 anos:** "No menor preço dos últimos 2 anos · ~2 avisos por semana (3 em grandes promoções)"

Para `docs/decisoes.md` (não vai para a tela), com desconto ≥ 50% e a métrica em R$: Selo em 7 de 10 · Novo recorde em 5 de 10 · Igual em 6 de 10 · Menor em 2 anos em 7 de 10.

## Resultado da Etapa 1c — régua da Steam (04/10/2026; `py tools/regua_steam.py --itad`, `py tools/backtest_tipos.py --so-steam`)

### 1. Os 5 rare deals da SteamDB (só preço Steam, BR)
4 dos 5 você **já tem** e não estão na lista de desejos. O Radar não coleta preço de jogos possuídos, então não tem nenhum histórico deles. Para o teste, o histórico veio da ITAD só em memória (nada gravado). Só o WRC 7 está na lista.

| Jogo | a) Agora (marcadas / Steam) | b) piso_tipo · Selo (F ou G) · só G | c) Menor antes do episódio, marcadas (loja, data) · última vez no nível | d) Só Steam: menor anterior · piso_tipo | e) Promoções anteriores · 1º registro |
|---|---|---|---|---|---|
| Ori and the Will of the Wisps (tem) | Steam R$ 12,90 / R$ 12,90 | raro · sim · **sim** | R$ 25,80 (Steam, 20/04/2023) · 04/05/2023 | R$ 25,80 · raro | 41 · 05/10/2021 |
| FINAL FANTASY XV (tem) | Steam R$ 37,50 / R$ 37,50 | novo · sim (F) · não | R$ 50,00 (Nuuvem 26/08/2026, Steam 04/08/2026, GMG 26/06/2026) · 15/09/2026 | R$ 50,00 (11/08/2026) · novo | 37 · 05/10/2021 |
| CrossCode (tem) | Steam R$ 12,00 / R$ 12,00 | raro · sim · **sim** | R$ 12,94 (Steam, 22/12/2022) · 05/01/2023 | R$ 12,94 · raro | 28 · 05/10/2021 |
| The Escapists (tem) | Steam R$ 9,49 / R$ 9,49 (SteamDB R$ 4,59) | 24m · não · não | R$ 3,59 (Steam, 28/03/2023) · 28/03/2023 | R$ 3,59 · 24m | 66 · 05/10/2021 |
| WRC 7 (lista, carrinho) | Steam R$ 2,39 / R$ 2,39 | novo · não · não | R$ 4,74 (Nuuvem, 15/07/2025) · 01/10/2026 | R$ 4,79 (19/09/2026) · **raro** | 46 · 04/10/2021 |

Por que o Radar dá ou não dá recorde raro:
- **Ori:** daria (se estivesse na lista): R$ 12,90 ≤ 50% de R$ 25,80, e o recorde anterior tem 41 meses.
- **CrossCode:** daria (se estivesse na lista): R$ 12,00 < R$ 12,94, e esse nível não aparecia havia 45 meses (≥ 18).
- **FINAL FANTASY XV:** nem só com a Steam dá. R$ 37,50 > 50% de R$ 50,00, e R$ 50,00 foi há 1,8 mês. A SteamDB usa outra regra. Pela regra antiga (F, "maior desconto da história", -70%), o Radar dava Selo.
- **The Escapists:** não é defeito. A Steam vende o jogo sozinho (pacote 60584) a R$ 9,49. O R$ 4,59 que a SteamDB mostra é a "melhor opção de compra", o pacote 80013 "The Escapists + The Escapists: The Walking Dead Deluxe". O Radar usa o pacote com o nome do jogo (regra de `decisoes.md`). Mesmo a R$ 4,59, não bateria o recorde de R$ 3,59 de 03/2023.
- **WRC 7:** é outra loja, por R$ 0,02. Só com a Steam dá (R$ 2,39 ≤ 50% de R$ 4,79 = R$ 2,40). Nas marcadas, a Nuuvem teve R$ 4,74 em 07/2025, então o limite cai para R$ 2,37, e o nível de R$ 4,74–4,79 apareceu em 10/2026 (a menos de 18 meses).

### 2. Selo da Steam (regra G só com a loja Steam)
- **Hoje, na lista:** 1 jogo, o WRC 7. Ele **não** é Selo G do Radar: a Nuuvem teve R$ 4,74 em 15/07/2025 (ver acima).
- **Backtest só com a Steam** (mesmo período; "não ficou mais barato" medido só na Steam):

| Variante | Eventos | Não ficou mais barato (R$) | Não batido +5 / +10 | Não voltou 6m | Média de avisos novos/sem. normal / grande | Hoje |
|---|---|---|---|---|---|---|
| Selo da Steam (G) | 55 | 78,2% | 87,3% / 90,9% | 34,5% | 0,2 / 0,8 | 1 |
| Selo do Radar (G, lojas marcadas; 1b) | 47 | 74,5% | 89,4% / 93,6% | 31,9% | 0,2 / 0,7 | 0 |
| Novo recorde na Steam ≥ 50% | 464 | 52,2% | 55,8% / 70,7% | 11,4% | 2,1 / 6,2 | 31 |
| Igual na Steam ≥ 50% | 3.110 | 66,3% | 67,1% / 79,6% | 6,3% | 13,8 / 43,2 | 180 |
| Menor em 2 anos na Steam ≥ 50% | 319 | 73,0% | 74,3% / 81,5% | 7,5% | 1,6 / 3,5 | 70 |

### 3. Novo recorde na Steam hoje
- **77 jogos**; 8 deles não são Novo recorde do Radar. Em todos, uma loja marcada teve preço menor ou igual antes.
- **Igual no Radar:**
  - POSTAL 4: Steam R$ 14,99; GMG R$ 15,00 em 03/2026, diferença ≤ R$ 0,10.
  - Invincible VS: Nuuvem R$ 119,40 em 08/2026.
  - Mixtape: Nuuvem R$ 47,99 em 09/2026.
- **Sem tipo no Radar:**
  - Street Fighter 6: Nuuvem R$ 68,99 em 08/2026.
  - The Alters: GMG R$ 45,39 em 08/2026.
  - DRAGON BALL: Sparking! ZERO: Nuuvem R$ 119,99 em 09/2026.
  - Escape from Ever After: GMG R$ 44,09 em 08/2026.
- **Menor em 2 anos no Radar:** Starfield, GMG R$ 99,00 em 2022/2023.

### 4. ITAD: menor preço da Steam sem baixar histórico (4 chamadas)
- **`deals/v2`** (só Steam) traz `storeLow` em 200 de 200 itens. É só o preço, **sem data**; em 5 de 200 difere do `historyLow`.
- **`games/storelow/v2`** traz o menor por loja **com data** (`timestamp`), 200 jogos por chamada. Exemplo: Steam R$ 2,96, -67%, 27/05/2024.
- **Dá para saber "o menor preço na Steam" dos ~65 mil jogos** sem histórico: as ~333+ chamadas do `deals/v2`, mais ~330 do `storelow/v2` para ter a data. Isso basta para Novo recorde e Igual ao recorde na Steam.
- **Não basta para o Selo (G)** nem para Menor em 2 anos:
  - o menor que vem pode ser o próprio preço de agora (falta o menor **antes** do episódio atual);
  - não há "última vez nesse nível", só uma data;
  - não há o menor dos últimos 24 meses (só `historyLow_1y` e `historyLow_3m`, de todas as lojas).

### 5. Custo de o Radar montar o histórico da Steam inteira (1 `Query` por dia, gravando só o que mudou)
- **Consulta:** 108 chamadas, ~2,5 min, ~126 MB baixados por dia (só os itens com desconto).
- **Duas consultas com 1 h de intervalo** (14:18 e 15:20 UTC, no meio da promoção de outono): 107.935 → 107.941 itens. **Mudaram 0 preços**, entraram 9 e saíram 3, ou seja, 12 registros. Dos itens, 106.288 terminam juntos em 08/10.
- **Tamanho:** 126 B por registro na tabela `preco` do Radar, com o índice (medido com 100 mil registros reais).
- **Estimativa** (a medição de 1 h no meio de uma promoção não mostra o dia típico):
  - 1º dia: ~108 mil registros ≈ **14 MB**.
  - Dia comum: provavelmente milhares de registros (< 1 MB).
  - Começo e fim de grande promoção: ~100 mil registros cada (≈ 13 MB). Com 4 grandes promoções por ano, ~0,8 milhão.
  - Com ~5 promoções por jogo por ano (o ritmo da lista no backtest, que tende a ser mais alto que o da Steam inteira), ~1,1 milhão.
  - **Por ano: ~1 a 1,5 milhão de registros, ≈ 130–190 MB.**
- **Limites:**
  - a `Query` só traz itens com desconto: a volta ao preço cheio é inferida pela saída da lista ou pelo `discount_end_date`;
  - o histórico começa do zero: o Selo (G) só fica confiável depois de ≥ 18 meses, a menos que se importe o passado da ITAD.

## Fora desta spec
- Veredito na ficha, keyshop "decente" e limpeza do resto das Configurações → **spec 05**.
- Seguidos, ignorados e família pela conta Steam sem `userdata.json` → **spec 06** (troca só `conta_steam.relacao`).
- Promoções da Steam inteira → **spec 07**, decidida com o item 1.6.
- Layout geral → **spec 08**.
- Filtros por tags, sistema e recursos (o Radar não coleta esses dados hoje).

## Aceite
1. A Etapa 1 foi entregue com a métrica em R$, a conferência do Selo (143 eventos / 71,3%) e os números de 1.2 a 1.6.
2. Com só o Selo ligado, uma rodada no banco de hoje avisa só jogos com Selo G (imprima quantos e quais). Não avisa ninguém por raridade nem por favorito (teste sem rede, numa cópia do banco).
3. Ligar "Novo recorde" passa a avisar um jogo com `piso_tipo == "novo"` e corte ≥ `desconto_minimo`; desligar para de avisar. Um jogo com `piso_tipo == "24m"` e corte < `desconto_minimo` não avisa. Um jogo Selo + novo recorde avisa com só "Novo recorde" ligado.
4. Ligar um tipo com N jogos já qualificados gera 1 toast de resumo e nenhum aviso individual. Os que entrarem depois avisam normalmente.
5. Na vitrine, nenhum jogo aparece em dois blocos, e "Ver tudo" abre Promoções com o chip certo, sem o filtro de análises, e o mesmo total N.
6. Em Promoções:
   - "✓ Monitorado por você" + "✕ Silenciado" funcionam combinados;
   - com "Qualquer um", "✓ Monitorado por você" + "✓ No carrinho" mostra a união;
   - as contagens batem com o total ao marcar a caixa;
   - ordenar por "Costuma voltar" põe "nunca teve esse desconto" primeiro, depois "não teve nos últimos 2 anos", e "histórico curto", "primeira promoção" e vazios por último;
   - nenhuma tela mostra Comum/Incomum/Raro/Ultrarraro/Lendário (`grep` no `painel.html` e no `notificador.py`);
   - sem estado salvo, a aba abre com os chips "Desconto ≥ 50%" e "Análises ≥ 5.000"; "Restaurar padrão" volta a eles.
7. Os chips refletem exatamente os filtros ativos, o × remove só aquele filtro e o estado volta igual ao recarregar.
8. Ordenar por "Termina" põe primeiro o que acaba antes; por "Começou", o que acabou de entrar. Shift+clique soma critérios, e os nulos ficam por último.
9. `/api/promocoes` com o cache pronto responde em ≤ 300 ms no banco real (imprima os tempos).
10. `grep` mostra `rgFollowedApps` e `rgIgnoredApps` lidos só em `radar/conta_steam.py`. Sem `userdata.json`, Seguido e Ignorado ficam desativados, com a dica, e nada quebra.
11. Funciona no celular (`max-width:720px`) e `py tools/checar.py` dá `ok`.
