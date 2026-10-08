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
- **Aviso de keyshop desligado por padrão (07/10/2026, 0.16).** No banco do dono, 22 dos 26 avisos enviados eram "Keyshop (GG.deals)": Half-Life, HL2, CS:Source e Opposing Force a R$ 7–9 avisando de novo a cada queda de centavos (o `preco_maximo` de R$ 10 pega qualquer clássico barato, e o "menor histórico" é o da própria GG.deals, que desce aos poucos). A GG.deals fica só como informação (ficha, flag e filtro de keyshop). Migração `keyshop_alerta_off` desliga também em quem já tinha o config.
- Não usar várias chaves da mesma API para driblar limite (termos de uso).

## Avaliação
- **Raridade v2 (0.14) mede o corte, não o preço.** A v1 media reais e chamava de Lendário qualquer centavo abaixo do piso: Castle of Illusion a 80% saía Lendário, mas 75% acontece todo mês; mudanças de preço base (HLM2 R$ 24,99 → R$ 46,99) também enganavam. Agora: episódios de promoção nas lojas marcadas, corte até 5 pontos abaixo = mesmo nível, frequência por ano em 24 meses (ver `arquitetura.md`). Promoção sem registro de fim "vence" em 45 dias; brindes (R$ 0) não contam.
- **Dois eixos separados:** raridade (frequência do corte) decide o alerta; a **pílula de piso** (reais) é só informação e nunca alimenta a raridade. "Recorde raro" é regra nossa (≥ 18 meses sem aquele nível ou ≤ 50% do recorde); a SteamDB não documenta a dela e só olha a Steam.
- **Lendário (regra C, 04/10):** nunca chegou a esse nível no histórico **inteiro** (que começa em 03/10/2021: limite da importação da ITAD), **com ≥ 24 meses de histórico e ≥ 1 promoção anterior** nas lojas marcadas; com 12–24 meses, no máximo Ultrarraro. Motivos: jogos de 1 ano "nunca chegaram" a quase nada (10 dos 22 Lendários eram de 12–23 meses), e sem promoção anterior é buraco nos dados — o ARK: Survival Evolved tinha só um brinde e um preço cheio nas lojas marcadas e saía Lendário com "42 meses de histórico". Sem promoção anterior: no máximo Incomum (logo, sem Selo).
- **Selo Kurokami = só G desde a 0.15 (04/10, spec 04).** F (Lendário, "maior desconto da história") saiu: na **escada de descontos** (o corte sobe um degrau por ano, ex.: Forza 20% → 30% → 40% → 50%) cada degrau novo vira "maior desconto da história" depois de 24 meses de histórico. No backtest de 04/10 (+5, corte) F acertava 67,5% e G 84,3%. Selo só G: 47 eventos, **74,5% não ficou mais barato em 12 meses (R$)**, 89,4% não batido +5, ~0,2 aviso por semana normal (0,7 em grandes promoções). **Folga de centavos na "metade" (04/10):** preço ≤ 50% do recorde anterior + R$ 0,10 ou 1% da metade (o que for maior), a mesma tolerância do "igual" (`analise._metade`). Caso real: WRC 7 a R$ 2,39 com recorde de R$ 4,74 (Nuuvem, 07/2025; metade R$ 2,37) ficava sem Selo por R$ 0,02. Com a folga o backtest não mudou (47 eventos, 74,5%) e hoje 1 jogo da lista tem Selo (WRC 7). `selo_motivo`: "preço caiu pela metade ou mais (o menor anterior era R$ X, mm/aaaa)" ou "o menor preço anterior (R$ X) foi há N meses". Frase para os textos do usuário: "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade". O Selo **contém o rare deal** (G), então não há opção "Recorde raro" separada; `piso_tipo == "raro"` sem promoção anterior conta como Novo recorde.
- **Avisos por tipo de recorde (0.15, spec 04).** O usuário escolhe em "O que te avisa": Selo (ligado), Novo recorde, Igual ao recorde, Menor em 2 anos (desligados). Fora o Selo, só com corte ≥ `desconto_minimo`. Backtest de 04/10 (`tools/backtest_tipos.py`, semanas 10/2022–10/2025, métrica do usuário = **não ficou mais barato em 12 meses, em R$**, nas lojas marcadas; média de avisos novos por semana normal / grande promoção):

  | Tipo (desconto ≥ 50%, exceto Selo) | Eventos | Não ficou mais barato | Não batido +5 | Avisos/semana | "em X de 10" |
  |---|---|---|---|---|---|
  | Selo (só G) | 47 | 74,5% | 89,4% | 0,2 / 0,7 | 7 |
  | Novo recorde | 493 | 45,0% | 56,8% | 2,3 / 6,4 | 5 |
  | Igual ao recorde | 2.765 | 59,0% | 63,7% | 13,5 / 33,7 | 6 |
  | Menor em 2 anos | 321 | 67,6% | 75,1% | 1,8 / 3,1 | 7 |
  | base: toda promoção | 10.761 | 38,0% | 46,9% | 54,8 / 122,4 | 4 |

  Ligar um tipo não dispara em massa (resumo único). **Igual ao recorde fica desligado por padrão** (~14 avisos por semana). Tabela completa e números da Etapa 1/1b/1c em `docs/specs/04-vitrine-promocoes-e-avisos.md`.
- **Raridade só informa (0.15).** Raro/Ultrarraro sem Selo deixaram de avisar (eram 26 dos 38 avisos de 04/10; backtest: 53,5% não batido, igual a "promoção no piso"). Os 5 nomes saíram de todas as telas e títulos: a raridade virou a coluna **"Costuma voltar"** (só informa). "Nunca teve esse desconto" só quando o nível não aparece no histórico inteiro; se apareceu antes dos últimos 24 meses, "não teve nos últimos 2 anos" (Valdis Story: -50% hoje, -75% em 03/2024).
- **Favoritos não têm exceção de aviso (0.15).** `favoritos_top` ignorado; todos seguem as 4 caixas.
- **Filtros no servidor (0.15).** A aba Promoções pede `/api/promocoes` (filtra, conta e pagina no Radar, sobre um cache em memória) em vez de baixar a lista inteira: assim a mesma tela serve para a Steam inteira (spec 07; ~108 mil itens com desconto no BR via `IStoreQueryService/Query`, sem chave, com `sort` fixo). Ao abrir pela primeira vez: "Desconto ≥ 50%" e "Análises ≥ 5.000", como a SteamDB (618 → 205 jogos em 04/10).
- *(até a 0.14)* **Selo Kurokami = F ou G (04/10).** **F** = Lendário (regra C): nenhum episódio anterior com corte ≥ corte atual − 5 pontos no histórico inteiro das lojas marcadas, com **≥ 24 meses** de histórico e **≥ 1 promoção anterior**. **G** = pílula Recorde raro + ≥ 1 promoção anterior nas lojas marcadas: preço atual abaixo do menor preço registrado antes do episódio atual (diferença > R$ 0,10 e > 1%) **e** (o preço esteve no nível desse recorde anterior pela última vez há **≥ 18 meses** **ou** preço atual **≤ 50%** do recorde anterior). Em ambos, corte ≥ `alerta.selo_corte_minimo` (padrão 0). Raro e Ultrarraro sozinhos não ganham Selo. Motivo (`selo_motivo`): F → "maior desconto da história (-85%; antes, no máximo -80%)"; G → "menor preço já registrado (dados desde mm/aaaa)" (mês/ano do primeiro registro nas lojas marcadas). **Não prometer** "raro" nem que não vai se repetir: o mesmo nível volta em até 6 meses em ~85% dos Selos.
  - *Frase para os textos do usuário (referência, não substitui a regra):* "o jogo está na melhor oferta da história dele: o maior desconto ou o menor preço em muito tempo".
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
  | F ou G (G sem exigir promoção anterior) | 147 | 70,1% | 86,4% | 15,0% | 1 / 3 |
  | **Selo final: F ou G, com ≥ 1 promoção anterior também na G** | 143 | **71,3%** | 87,4% | 15,4% | **1 / 3** |
  | alertas sem Selo (Raro/Ultrarraro, desconto mínimo) | 679 | 53,5% | 69,1% | 11,9% | 5 / 13,5 |
  | base: toda promoção | 10.725 | 47,0% | 64,1% | 9,4% | 91 / 211,5 |
  | base: toda promoção no piso | 8.481 | 52,1% | 69,4% | 7,6% | 71 / 178,5 |

  **Por que F ou G:** é a única que cumpre as duas metas (por 0,1 ponto: dentro da margem de erro, empata com a E, que é mais complexa). F e G quase não se sobrepõem (24 casos), então somam volume sem perder acerto. A G sozinha acerta mais, mas tem só 51 casos em 3 anos. A regra antiga (A) acertava o mesmo que "toda promoção no piso". Os motivos de erro eram reais, não do backtest: escada de descontos (o corte do jogo sobe ano a ano) e mudança de patamar (o novo máximo vira o normal). Ressalvas: usa a lista de hoje (viés de sobrevivência); as semanas das grandes promoções são aproximadas; G/H são decididas em reais e "batido" é medido em corte.
- **Recorde em reais por si só (H) acerta menos que qualquer promoção** (33,9% contra 47%): recorde por centavos logo é batido. Por isso "Novo recorde" vem **desligado** e, ligado, exige `desconto_minimo` (com ≥ 50%: 56,8% não batido +5, 45% em R$).
- **G também exige ≥ 1 promoção anterior (04/10, decisão do dono):** sem isso, a **primeira promoção** de um jogo com preço ≤ 50% do cheio virava Recorde raro (o "recorde anterior" era o preço cheio) — mesmo buraco de dados do ARK. No backtest eram 4 de 51 casos de G, com 25% de acerto; sem eles o Selo foi de 70,1% para 71,3%. A **pílula** continua dizendo "Recorde raro" nesse caso; só o Selo não sai.
- **Régua da Steam é só informação (04/10, spec 04).** A SteamDB marca "rare deal" olhando só a Steam; o Radar olha as lojas marcadas. Na régua de 04/10 (5 rare deals da SteamDB): Ori e CrossCode dariam Selo também no Radar (mas você já os tem, e o Radar não coleta possuídos); FINAL FANTASY XV não dá nem só com a Steam (R$ 37,50 > 50% de R$ 50,00 de 08/2026); The Escapists é outro pacote (R$ 4,59 = "+ The Walking Dead Deluxe"; o jogo sozinho custa R$ 9,49); WRC 7 perde por R$ 0,02 (Nuuvem R$ 4,74 em 07/2025). Na lista de hoje: 1 Selo e 8 Novos recordes só da Steam. Backtest só Steam: Selo 55 eventos, 78,2% não ficou mais barato (Radar: 47 e 74,5%). Decisão: as lojas marcadas decidem tudo; quando só a Steam dá Novo recorde ou Selo, a ficha mostra "Na Steam, é o menor preço já registrado. Nas suas lojas, <loja> já teve R$ X (mm/aaaa)." (`analise.regua_steam`).
- **"Termina em breve" usa o mesmo `max_por_rodada`** (carrinho primeiro, depois o que acaba antes; o resto vira "+N terminando em breve"): no fim de um evento da Steam, 36 de 44 alertas acabavam na mesma janela de 24 h.
- **Análises não decidem nada** (o jogo já está na lista de desejos): saíram do score e dos filtros de alerta. Na aba Promoções, análises e nota filtram só a tela. Score = corte × peso da raridade + 10 no piso, só interno.
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
- **Sem ponte do Tampermonkey (removida na 0.16, pedido do dono: era remendo).** O navegador não deixa `localhost` usar a sessão da Steam; o carrinho vai pela extensão própria do Radar (abaixo). Adicionar à lista de desejos pelo painel saiu junto (dependia da ponte).

- **Steam inteira (spec 07):** `IStoreQueryService/Query` exige `sort: 2` (sem ele a paginação repete e pula itens). Peça gzip (`rede.http_json` já pede): sem ele são 1,5 MB por página (126 MB numa grande promoção). Coleta incompleta não troca o retrato. **Sem histórico** (decisão do dono, 08/10): cada coleta substitui o retrato; a cada hora e no "Verificar agora". Avisos continuam só para a lista (a Steam inteira daria centenas por dia).

## Login Steam e segurança dos usuários (spec 06)
- **"Entrar pela Steam" = OpenID 2.0** (como ITAD, GG.deals e SteamDB): confirma na página da Steam; o Radar só guarda o SteamID em `config.perfil_steam`. Nada de senha, token ou cookie. O OpenID só prova quem é: não dá acesso ao carrinho nem a lista privada.
- **Regras do retorno (`steam_openid.py`, testadas em `tools/testar_openid.py`):** `state` aleatório de uso único (5 min) dentro do `return_to` (impede alguém forçar a troca de conta), `return_to` e `op_endpoint` exatos, `claimed_id` de 17 dígitos igual a `identity`, campos obrigatórios assinados, nonce recente e nunca repetido, e confirmação `check_authentication` na própria Steam. A URL de retorno é montada pelo servidor (`localhost`), nunca pelo cabeçalho `Host`. As rotas só respondem ao próprio PC; página de erro escapa o texto e não repete o que veio na URL.
- **Carrinho pela extensão do Radar (0.16, `extensao/`, no lugar do QR):** o login por QR saiu porque a Steam o tratava como celular novo e alertou o dono de conta invadida. O painel não alcança a sessão da Steam (outro site; o localStorage também é separado por site), então quem põe no carrinho é uma extensão própria (Manifest V3, sem Tampermonkey). **Finalizar pedido** abre `store.steampowered.com/cart/#kurokami=PAIS:p<subid>[-presente|-privado],b<bundleid>[-modo]`; a extensão lê o `webapi_token` da própria página (`#application_config` → `data-store_user_config`, reserva `/pointssummary/ajaxgetasyncconfig`), chama `IAccountCartService` (`GetCart`/`AddItemsToCart`) pelo service worker (sem CORS) e recarrega. O token nunca sai do navegador nem chega ao Radar. Só adiciona o que ainda não está lá, em qualquer modo (`flags.is_gift`/`is_private`), confere lendo de volta e nunca remove. Sem login, guarda o pedido em `sessionStorage` (15 min) e completa depois de entrar. Instalação: **sem loja** (decisão do dono), "Carregar sem compactação" apontando para `{app}\extensao` (o instalador copia); o painel detecta a extensão por `data-kurokami-ext` no `<html>` e, sem ela, oferece o assistente ao abrir (pede permissão; o usuário ainda liga o Modo do desenvolvedor e arrasta a pasta). **Instalar sozinho não existe:** `--load-extension` foi desligado no Chrome em 2025 e registro/políticas do Windows doméstico só aceitam extensões da Web Store. Qualquer link `store.steampowered.com/cart/#kurokami=…` aberto por quem tem a extensão e está logado põe itens no carrinho (sem clique no painel): aceito, porque o pior caso é encher o carrinho, nunca comprar. Atualizações do Radar trocam os arquivos na mesma pasta (o navegador recarrega ao reabrir). Quem tinha sessão QR: `painel._limpar_sessao_qr` revoga na Steam e apaga do cofre (`steam_refresh`) ao abrir. Rotas `/api/steam/*` continuam só do próprio PC, com `Host` fixo e `Origin` obrigatório. **O carrinho do Radar é só da Steam**, com `modo` por item: `conta`, `presente`, `privado`.

## Produto (preferências do usuário)
- Visual da **loja Steam** (cores Valve, caixas de preço com desconto verde, hover estilo Steam).
- Avisar **pouco e bem**: raridade, linha de base, um alerta por jogo, limite por rodada.
- Interface e mensagens em **português**; termos como score, bundle, keyshop ficam como estão.
- Nada pessoal no repositório (perfil, chaves, userdata). O projeto é público e usado por amigos.
