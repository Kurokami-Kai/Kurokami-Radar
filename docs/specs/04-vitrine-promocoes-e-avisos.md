# Spec 04 — Vitrine, aba Promoções e avisos por tipo de recorde

Status: **Etapa 1 a fazer** (substitui a spec 04 anterior, "Filtros, colunas e DLCs em promoção") · Pedido do dono em 04/10/2026 · Skills: `kurokami-code`, `testar-sem-rede`, `coleta-e-apis` (Etapa 1), `editar-painel` (Etapa 2)

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
3. **Não favorito avisa** se existe `t` em `tipos` com `alerta.tipos[t]` ligado e:
   - `t == "selo"` (o `selo_corte_minimo` já está dentro de `an["selo"]`); **ou**
   - corte ≥ `alerta.desconto_minimo`.
4. **Favorito** (posições 1..`favoritos_top`) avisa se `tipos` não estiver vazio, mesmo com os tipos desligados e sem desconto mínimo. Isso substitui a regra "a partir de Incomum".
5. **Raridade não decide mais aviso.**
   - `alerta.raridade_minima` passa a ser ignorado (fica no config por compatibilidade).
   - Raro e Ultrarraro sem Selo deixam de avisar.
   - A raridade continua calculada e exibida.
   - Os avisos de keyshop e de modo completo não mudam.
6. **Ligar um tipo não dispara em massa.**
   - Guarde em `meta.tipos_ligados` os tipos da última rodada.
   - Quando um tipo passa de desligado para ligado, os jogos que avisariam só por causa dele entram em `notificado` sem toast. Sai um único toast: "<Tipo> ligado: N jogos já estão assim agora. Você vai receber só os próximos.", com o botão "Ver", que abre a vitrine.
   - Sem `meta.tipos_ligados` (primeira rodada da 0.15), grave os tipos atuais sem toast.
7. **Título e motivo do aviso** (use `piso_ref`; confira que, no caso `24m`, ele traz o menor de sempre, senão use o menor de sempre das lojas marcadas):

   | Tipo | Título | Motivo |
   |---|---|---|
   | `selo` | "SELO KUROKAMI · <jogo>" | o que já existe |
   | `novo` | "Novo recorde · <jogo>" | "menor preço já registrado (antes R$ X em mm/aaaa)" |
   | `igual` | "Igual ao recorde · <jogo>" | "mesmo preço do menor já registrado (mm/aaaa)" |
   | `24m` | "Menor em 24 meses · <jogo>" | "menor preço em 2 anos (o menor de sempre foi R$ X em mm/aaaa)" |

8. **Ordem** da saída e do `max_por_rodada`: selo, novo, igual, 24m; dentro de cada tipo, maior corte primeiro.
9. `vale` passa a significar "avisaria agora". O "termina em breve" não muda. Os itens de `ultimos_alertas` ganham `tipos` e `tipo_oferta`.

### B. Dados da conta Steam: uma função só
- Arquivo novo `radar/conta_steam.py` com `relacao(cfg) -> {"seguidos": set[int], "ignorados": set[int], "fonte": "userdata" | None, "quando": iso | None}`.
- Ela lê `rgFollowedApps` e as chaves de `rgIgnoredApps` (str → int) do arquivo achado por `caminhos.achar_userdata`.
- Cache pela data de modificação do arquivo; nunca grava no banco; em caso de falha, devolve conjuntos vazios e `fonte = None`.
- **Nenhum outro módulo lê essas duas chaves.**
- Na docstring: "a spec 06 (login por QR) troca só esta função".

### C. Filtros no Radar (servidor)
1. **Cache das linhas.** `painel.linhas_promocoes()` monta, por jogo, os campos de `/api/lista` mais `inicio`, `tipos`, `tipo_oferta`, `na_lista`, `tenho` (`possuido` ou `tenho_manual`), `no_carrinho`, `em_bundle`, `seguido` e `ignorado_steam`.
   - Fica em memória, com lock.
   - É refeito quando termina uma coleta, quando o config é gravado, nos POST de silenciar, extra, tenho, carrinho, modo e dlc, e quando o userdata.json muda de data.
2. **`GET /api/promocoes?q=<JSON url-encoded>`**
   - Campos de `q`: `busca`, `relacao{campo: "exigir"|"excluir"}`, `qualquer_um` (bool), `mostrar_so[]`, `tipo[]`, `raridade[]`, `outros[]`, `preco_de`/`preco_ate` (centavos), `analises_de`/`analises_ate`, `nota_min`, `desconto_min`, `lanc_de`/`lanc_ate` (aaaa-mm-dd), `em_breve` (bool), `ordem` ([[campo, "asc"|"desc"], ...]), `pagina` (a partir de 1). São 100 itens por página.
   - Resposta: `{total, pagina, itens[], contagens{mostrar_so{selo,novo,igual,24m}, raridade{...}, tipo{jogo,dlc}}, conta{tem_dados, quando}}`.
   - Cada contagem é calculada com todos os outros filtros aplicados, menos o do próprio grupo (como na SteamDB).
3. **Combinação dos filtros.**
   - Os grupos se combinam com E.
   - Dentro de Mostrar só, Tipo, Raridade e Outros, as caixas se combinam com OU.
   - Na Relação, os "exigir" se combinam com E (ou com OU se `qualquer_um`), e os "excluir" sempre excluem.
   - Um item sem o valor de uma faixa ativa (ex.: sem data de lançamento com o filtro de lançamento ligado) fica fora.
4. **Ordenação.**
   - Campos permitidos: `nome`, `corte`, `preco`, `raridade` (lendario > ultrarraro > raro > incomum > comum > sem promoção), `nota` (rpos/rcount), `analises` (rcount), `lancamento`, `fim`, `inicio`.
   - Valores nulos ficam sempre por último; o desempate final é o appid.
   - Padrão: corte desc, depois nome asc.
5. **Validação:** campo ou valor desconhecido → 400 com mensagem em português; campos ausentes = sem filtro.
6. **Desempenho:** com o cache pronto, ≤ 300 ms no banco real. Meça e informe também o tempo da primeira montagem.
7. **`GET /api/vitrine`:** `{selo{total, itens≤10}, novo{total, itens≤8}, igual{...}, "24m"{...}, avisa{selo, novo, igual, 24m}}`, a partir do mesmo cache.
8. `/api/lista` continua existindo, com os campos novos. A vitrine e a aba Promoções deixam de usá-la.

### D. Painel

**D1. Aba "Vale a pena" = vitrine**, no padrão das prateleiras da loja Steam.
- **Topo:** carrossel "Selo Kurokami" (reaproveite o `hero`), com até 10 jogos de `tipo_oferta == "selo"` e "Ver tudo (N)". Se estiver vazio: "Nenhum jogo com Selo agora."
- **Abaixo, nesta ordem:** blocos "Novo recorde", "Igual ao recorde", "Menor em 24 meses".
  - Cada jogo aparece em um bloco só (`tipo_oferta`).
  - Os três blocos respeitam `alerta.desconto_minimo`.
  - Bloco vazio não aparece.
- **Cada bloco tem:**
  - título com 🔔 se o tipo avisa;
  - subtítulo de uma linha: "o menor preço que já registramos" / "o mesmo preço do menor já registrado" / "o menor preço dos últimos 2 anos (já esteve mais barato antes)";
  - grade de até 8 capas (4 × 2; 2 colunas em `max-width:720px`), por corte desc e depois preço asc;
  - "Ver tudo (N)".
- **Capa:** arte, nome, caixa de preço da Steam, botão + do carrinho e, se faltar menos de 72 h, "⏳ termina em…". Sem outras pílulas.
- **"Ver tudo"** abre Promoções com Mostrar só = aquele tipo e, fora do Selo, "Desconto ≥ `desconto_minimo`". O total exibido ali é o mesmo N.
- **Sai da aba:**
  - a lista "Todos que valem a pena";
  - as pílulas Todos/Selo/Lendário/Ultrarraro+/Raro+/Incomum+;
  - a legenda da raridade;
  - a faixa "Promoções raras da sua lista… / Ver a lista inteira".
- **Contador do topo da página:** "N na vitrine · M na lista".

**D2. Aba "Lista de desejos" passa a se chamar "Promoções"** em todos os textos visíveis (o id interno pode continuar `lista`). É um explorador que começa sem filtros e usa `/api/promocoes`.

A lateral fica à direita. Em `max-width:720px`, vira um botão "Filtros" que abre um painel. Os filtros aplicam na hora (espera de 250 ms na digitação), o estado fica salvo no navegador (`ls.set`) e há um botão "Limpar filtros". De cima para baixo:

1. **Busca por nome.**
2. **"Sua relação com o jogo"**, cada linha com 3 estados: ✕ esconder / — tanto faz / ✓ só esses.

   | Linha | Campo |
   |---|---|
   | Na lista de desejos | `na_lista` |
   | Monitorado por você | `extra` |
   | Favorito | `favorito` |
   | No carrinho | `no_carrinho` |
   | Seguido na Steam | `seguido` |
   | Ignorado na Steam | `ignorado_steam` |
   | Silenciado | `mudo` |
   | Tenho | `tenho` |
   | Tenho o jogo base | `base_tenho` |

   - Caixa "Qualquer um": os ✓ passam a valer com OU.
   - Sem dados da conta (`conta.tem_dados` falso): Seguido e Ignorado ficam desativados, com a dica "precisa dos dados da sua conta Steam".
3. **"Mostrar só"**, combinadas com OU, cada caixa com uma bolinha na cor da sua pílula: Selo Kurokami · Novo recorde · Igual ao recorde · Menor em 24 meses (`tipo_oferta`). Cada caixa mostra a sua contagem.
4. **Listas recolhíveis**, com ponto azul no título quando há algo marcado:
   - **Tipo:** Jogo, DLC.
   - **Raridade:** Lendário, Ultrarraro, Raro, Incomum, Comum, Sem promoção. Cada nível só ele, sem "+".
   - **Outros:** Só em promoção · Em bundle · Modo completo · Keyshop bem mais barata (usa o campo `keyshop` atual; a spec 05 troca a regra).
5. **Faixas:**
   - Preço de/até (R$);
   - Análises de/até;
   - Nota ≥ (0–100%, passo 5);
   - Desconto ≥ (0–100%, passo 5);
   - Lançamento de/até + "Só em breve".

   Análises e nota filtram só a tela, nunca aviso.

**Chips** acima da tabela: um por filtro ativo (ex.: "Selo Kurokami", "Desconto ≥ 50%", "✓ Favorito", "✕ Silenciado"). O × remove só aquele filtro.

**Tabela (padrão):**
- **Colunas:**
  - capa;
  - nome, com o Selo e a pílula de recorde ao lado;
  - %, na caixa verde;
  - Preço;
  - Raridade (pílula);
  - Análises (%, com a cor de `revClass`);
  - Lançamento;
  - Termina ("em 5 dias"; vazio se não houver data);
  - Começou ("há 2 dias");
  - botão + do carrinho.
- **Ordenação:** clique ordena e inverte; Shift+clique soma critérios. A seta mostra a direção e o número mostra a ordem dos critérios.
- **Visualização em Grade:** usa um seletor com os mesmos critérios.
- **"Mostrar mais":** carrega a próxima página.
- **No celular:** a tabela rola na horizontal dentro do próprio contêiner, sem a página rolar de lado.

**Sai da aba:**
- a barra azul de atalhos;
- as pílulas cumulativas de raridade;
- "Restringir por preço", "Desconto mínimo", "Análises de usuários" e "Restringir por";
- as visualizações em linhas e compacta;
- o seletor "Ordenar por".

**D3. Ficha:** mostrar "Termina em" sempre que houver data, e não só abaixo de 72 h. O resto da ficha é da spec 05.

**D4. Configurações:** o bloco "O que vale a pena" passa a se chamar **"O que te avisa"**.
- **4 caixas** (Selo Kurokami, Novo recorde, Igual ao recorde, Menor em 24 meses).
  - Cada caixa tem uma linha fixa com os números da Etapa 1 (com o `desconto_minimo` padrão): "Em X de 10 vezes, o jogo não ficou mais barato nos 12 meses seguintes · ~N avisos por semana (M em grandes promoções)".
  - Registre a data do backtest em `docs/decisoes.md`.
- **"Desconto mínimo (%)":** com a dica "vale para Novo recorde, Igual e Menor em 24 meses".
- **"Selo Kurokami: desconto mínimo (%)":** fica como está.
- **Favoritos:**
  - o texto passa a ser "Você tem N favoritos: eles avisam em qualquer tipo, sem desconto mínimo";
  - com N = 0: "Sua lista de desejos não tem ordem: ordene-a na Steam para ter favoritos".
- **Saem:** "Avisar a partir de" e a dica do Score. O resto da aba é da spec 05.

**D5. Biblioteca → "DLCs em promoção"**
- **O que entra:** DLCs relevantes (`relevantes()`) que o usuário não tem, de jogos que ele tem, com desconto agora.
- **O que mostra:** capa, nome, jogo pai, preço, corte, pílula de recorde, Termina e botão + do carrinho.
- **Preço:** se o preço vier só da Steam (Etapa 1.4), escreva "preço Steam".

### E. Docs
- `docs/api.md`: `/api/promocoes`, `/api/vitrine` e os campos novos de `/api/lista`.
- `docs/dados.md`: `alerta.tipos`, `meta.tipos_ligados` e `raridade_minima` ignorado.
- `docs/arquitetura.md`: a regra de aviso, o cache das linhas e o `conta_steam`.
- `docs/decisoes.md`:
  - avisos por tipo, com a tabela da Etapa 1;
  - Raro/Ultrarraro sem Selo deixam de avisar;
  - o Selo contém o rare deal;
  - filtros no servidor, pensando na Steam inteira.
- `docs/pendencias.md`: marcar como resolvido o item "Decidir se Raro/Ultrarraro sem Selo continuam alertando".
- `README.md` e a seção `## 0.15.0` de `docs/novidades.md`, em linguagem de usuário.
- Ao terminar, rode `py tools/gerar_referencia.py`.

## Fora desta spec
- Veredito na ficha, keyshop "decente" e limpeza do resto das Configurações → **spec 05**.
- Seguidos, ignorados e família pela conta Steam sem `userdata.json` → **spec 06** (troca só `conta_steam.relacao`).
- Promoções da Steam inteira → **spec 07**, decidida com o item 1.6.
- Layout geral → **spec 08**.
- Filtros por tags, sistema e recursos (o Radar não coleta esses dados hoje).

## Aceite
1. A Etapa 1 foi entregue com a métrica em R$, a conferência do Selo (143 eventos / 71,3%) e os números de 1.2 a 1.6.
2. Com só o Selo ligado, os avisos de uma rodada são os de hoje menos os Raro/Ultrarraro sem Selo (teste sem rede, numa cópia do banco).
3. Ligar "Novo recorde" passa a avisar um jogo com `piso_tipo == "novo"` e corte ≥ `desconto_minimo`; desligar para de avisar. Um favorito em `24m` avisa com o tipo desligado e corte abaixo do mínimo. Um jogo Selo + novo recorde avisa com só "Novo recorde" ligado.
4. Ligar um tipo com N jogos já qualificados gera 1 toast de resumo e nenhum aviso individual. Os que entrarem depois avisam normalmente.
5. Na vitrine, nenhum jogo aparece em dois blocos, e "Ver tudo" abre Promoções com o chip certo e o mesmo total N.
6. Em Promoções:
   - marcar só "Ultrarraro" não mostra Lendários;
   - "✓ Favorito" + "✕ Silenciado" funcionam combinados;
   - com "Qualquer um", "✓ Favorito" + "✓ No carrinho" mostra a união;
   - as contagens batem com o total ao marcar a caixa.
7. Os chips refletem exatamente os filtros ativos, o × remove só aquele filtro e o estado volta igual ao recarregar.
8. Ordenar por "Termina" põe primeiro o que acaba antes; por "Começou", o que acabou de entrar. Shift+clique soma critérios, e os nulos ficam por último.
9. `/api/promocoes` com o cache pronto responde em ≤ 300 ms no banco real (imprima os tempos).
10. `grep` mostra `rgFollowedApps` e `rgIgnoredApps` lidos só em `radar/conta_steam.py`. Sem `userdata.json`, Seguido e Ignorado ficam desativados, com a dica, e nada quebra.
11. Funciona no celular (`max-width:720px`) e `py tools/checar.py` dá `ok`.
