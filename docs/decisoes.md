# Decisões e armadilhas já resolvidas

Leia antes de mexer em coleta, preços ou avaliação: cada item abaixo já foi um bug real.

## Steam
- `IStoreBrowseService/GetItems` só aceita **GET** com `input_json` na query (POST dá 405). `rede.servico_steam` tenta GET e só cai para POST em 405.
- `GetDLCForApps` exige chave de **parceiro** da Valve (401 com chave comum). O plano B é `appdetails` da loja (1 jogo por chamada, ~1,6 s). Fica marcado em `meta.dlcforapps_bloqueado`.
- **"DLCs não aparecem" logo depois de instalar** era a fila do plano B, não um defeito nos dados: a 0.12 aplicava `chamadas_lentas_por_rodada` (120) também na 1ª verificação, e ~1250 jogos levavam horas para ter a lista. A 0.13 faz a 1ª verificação completa (`meta.ult_completa`) e a ficha diz o motivo quando não há DLCs (`dlcs_estado`: não consultada/fila X/Y, Steam não informou, consulta falhou).
- Falha no plano B grava `consulta_lenta` tipo **`dlcs_falha`**, separado de `dlcs`: não conta como consultado, o jogo volta na próxima rodada; o sucesso apaga a marca.
- **Preço base não é o pacote mais barato.** HITMAN World of Assassination vende a "Part One" (R$ 8,89) no mesmo app. `steam._edicao_base` prefere o pacote com o mesmo nome do app; pacotes menores viram `papel='parcial'` e não servem para "completar".
- Pacote de **R$ 0 em jogo pago** é teste/fim de semana grátis: ignorado (`_edicoes`).
- `GetItems` não lista as DLCs de uma edição; o conteúdo vem de `packagedetails`. Às vezes nem lá → o usuário define com `radar.py conteudo` (`meta.edicoes_manuais`).
- A wishlist e o SteamID saem do perfil público, **sem chave** (XML `?xml=1`). Chave da Steam é opcional.

## IsThereAnyDeal / GG.deals
- ITAD manda horário com fuso (+02:00). Tudo é convertido para **UTC** antes de gravar; a ordenação é por texto.
- Na ITAD a **mesma loja pode vir 2x** (edições diferentes). `itad.precos` fica com uma por loja: a mais barata com DRM Steam.
- A oferta da **própria Steam vem sem DRM** na ITAD; é tratada como DRM Steam. Em outras lojas, DRM vazio = desconhecido.
- O **"preço atual" sai de `oferta_atual`**, nunca do último registro do histórico (ARK aparecia "grátis" por um brinde de 2022 de uma loja que parou de vender).
- Histórico importado é de **todas as lojas** (mesmo custo); o config só decide quais alertam.
- GG.deals lê a edição parcial em jogos como HITMAN → seus números são ignorados nesses jogos.
- Não usar várias chaves da mesma API para driblar limite (termos de uso).

## Avaliação
- **Raridade v2 (0.14) mede o corte, não o preço.** A v1 media reais e chamava de Lendário qualquer centavo abaixo do piso: Castle of Illusion a 80% saía Lendário, mas 75% acontece todo mês; mudanças de preço base (HLM2 R$ 24,99 → R$ 46,99) também enganavam. Agora: episódios de promoção nas lojas marcadas, corte até 5 pontos abaixo = mesmo nível, frequência por ano em 24 meses (ver `arquitetura.md`). Promoção sem registro de fim "vence" em 45 dias; brindes (R$ 0) não contam.
- **Dois eixos separados:** raridade (frequência do corte) decide o alerta; a **pílula de piso** (reais) é só informação e nunca alimenta a raridade. "Recorde raro" é regra nossa (≥ 18 meses sem aquele nível ou ≤ 50% do recorde); a SteamDB não documenta a dela e só olha a Steam.
- **Lendário (regra C, 04/10):** nunca chegou a esse nível no histórico **inteiro** (que começa em 03/10/2021: limite da importação da ITAD), **com ≥ 24 meses de histórico e ≥ 1 promoção anterior** nas lojas marcadas; com 12–24 meses, no máximo Ultrarraro. Motivos: jogos de 1 ano "nunca chegaram" a quase nada (10 dos 22 Lendários eram de 12–23 meses), e sem promoção anterior é buraco nos dados — o ARK: Survival Evolved tinha só um brinde e um preço cheio nas lojas marcadas e saía Lendário com "42 meses de histórico". Sem promoção anterior: no máximo Incomum (logo, sem Selo).
- **Selo Kurokami = F ou G (04/10)**: o jogo está na melhor oferta da história dele: o maior desconto ou o menor preço em muito tempo. **F** = Lendário (regra C); **G** = pílula Recorde raro (novo recorde em reais e o recorde anterior visto pela última vez há ≥ 18 meses, ou preço ≤ 50% dele). Em ambos, corte ≥ `selo_corte_minimo`. Raro e Ultrarraro sozinhos não ganham Selo. O motivo diz qual bateu: "maior desconto da história (-85%; antes, no máximo -80%)" ou "menor preço desde mm/aaaa" (início do histórico). **Não prometer** "raro" nem que não vai se repetir: o mesmo nível volta em até 6 meses em ~85% dos Selos.
- **Backtest do Selo** (`tools/backtest_selo.py`, banco de 04/10, 723 jogos da lista, semanas de 10/2022 a 10/2025, só com o histórico conhecido em cada data; cada Selo conta uma vez por episódio). **Meta fixada antes de olhar os resultados:** "não batido" (sem corte ≥ Selo + 5 em 12 meses) **≥ 70%** e **≤ 3 Selos por semana normal** (mediana).

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
  | **F ou G (escolhida)** | 147 | **70,1%** | 86,4% | 15,0% | **1 / 3** |
  | alertas sem Selo (Raro/Ultrarraro, desconto mínimo) | 679 | 53,5% | 69,1% | 11,9% | 5 / 13,5 |
  | base: toda promoção | 10.725 | 47,0% | 64,1% | 9,4% | 91 / 211,5 |
  | base: toda promoção no piso | 8.481 | 52,1% | 69,4% | 7,6% | 71 / 178,5 |

  **Por que F ou G:** é a única que cumpre as duas metas (por 0,1 ponto: dentro da margem de erro, empata com a E, que é mais complexa). F e G quase não se sobrepõem (24 casos), então somam volume sem perder acerto. A G sozinha acerta mais, mas tem só 51 casos em 3 anos. A regra antiga (A) acertava o mesmo que "toda promoção no piso". Os motivos de erro eram reais, não do backtest: escada de descontos (o corte do jogo sobe ano a ano) e mudança de patamar (o novo máximo vira o normal). Ressalvas: usa a lista de hoje (viés de sobrevivência); as semanas das grandes promoções são aproximadas; G/H são decididas em reais e "batido" é medido em corte.
- **Recorde em reais por si só (H) acerta menos que qualquer promoção** (33,9% contra 47%): recorde por centavos logo é batido. Por isso a pílula azul "Novo recorde" é só informação e **nunca alerta**.
- **Pendente:** pela regra G como foi escrita, a **primeira promoção** de um jogo com preço ≤ 50% do cheio vira Recorde raro (o "recorde anterior" é o preço cheio). No backtest foram 4 de 51 casos de G, com 25% de acerto; sem eles, F ou G daria 71,3%. Hoje nenhum jogo está assim. Exigir ≥ 1 promoção anterior também na G (como na F) aguarda o dono.
- **"Termina em breve" usa o mesmo `max_por_rodada`** (carrinho primeiro, depois o que acaba antes; o resto vira "+N terminando em breve"): no fim de um evento da Steam, 36 de 44 alertas acabavam na mesma janela de 24 h.
- **Análises não decidem nada** (o jogo já está na lista de desejos): saíram do score e dos filtros de alerta. Score = corte × peso da raridade + 10 no piso, só para ordenar.
- **`priority` 0 da wishlist = "sem posição"**, não "topo": quem nunca ordenou a lista tem tudo em 0, e com `favoritos_top` todos viravam favoritos. Favorito = posição 1..N.
- Diferenças de centavos (≤ R$ 0,10 ou 1%) contam como "igual" ao piso.
- "Completo" = combinação mais barata de edições/bundles/avulsos que cobre base + DLCs relevantes (`melhor_combinacao`, força bruta em até 14 opções). Pacotes (`classe=pacote`) contam por padrão.
- Séries: agrupadas pelo **nome** (`series.py`), não pelo campo franquia da Steam ("EA Play" não é série).

## App / Windows
- Gravações do painel competem com a coleta pelo SQLite: `timeout=30` e o carrinho em **arquivo próprio**.
- Atualizar arquivos com o Radar aberto deixa o processo velho servindo a página nova (404 nas rotas novas). O painel compara `VERSAO_PAGINA` (no HTML) com a versão do servidor e avisa. **Sempre atualizar os dois juntos.**
- **0.12 → 0.13:** a 0.12 nunca gravou `meta.ult_completa`, então a primeira abertura depois de atualizar faz uma **verificação completa (30 a 40 min)**. Esperado, não é bug.
- `getpass` no Windows não aceita colar → chaves entram por janela Tk.
- Instalado não pode gravar na própria pasta → dados em `%LOCALAPPDATA%` e migração única de `C:\Kurokami Radar`.
- Toasts: XML montado com escape + `-EncodedCommand`; o `$` de "R$" quebrava a interpolação do PowerShell.
- Ponte: o navegador não deixa `localhost` usar a sessão da Steam. Só um userscript **na própria Steam** consegue, sem expor cookies.

## Produto (preferências do usuário)
- Visual da **loja Steam** (cores Valve, caixas de preço com desconto verde, hover estilo Steam).
- Avisar **pouco e bem**: raridade, linha de base, um alerta por jogo, limite por rodada.
- Interface e mensagens em **português**; termos como score, bundle, keyshop ficam como estão.
- Nada pessoal no repositório (perfil, chaves, userdata). O projeto é público e usado por amigos.
