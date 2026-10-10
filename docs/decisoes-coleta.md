# Decisões: coleta (Steam, ITAD, GG.deals)

Leia antes de mexer em `steam.py`, `itad.py`, `ggdeals.py`, `coleta.py` ou `rede.py`.

### Steam
- `IStoreBrowseService/GetItems` só aceita **GET** com `input_json` na query (POST dá 405). `rede.servico_steam` tenta GET e só cai para POST em 405.
- `GetDLCForApps` exige chave de **parceiro** da Valve (401 com chave comum). O plano B é `appdetails` da loja (1 jogo por chamada, ~1,6 s). Fica marcado em `meta.dlcforapps_bloqueado`.
- **"DLCs não aparecem" logo depois de instalar** era a fila do plano B, não um defeito nos dados: a 0.12 aplicava `chamadas_lentas_por_rodada` (120) também na 1ª verificação, e ~1250 jogos levavam horas para ter a lista. A 0.13 faz a 1ª verificação completa (`meta.ult_completa`) e a ficha diz o motivo quando não há DLCs (`dlcs_estado`: não consultada/fila X/Y, Steam não informou, consulta falhou).
- Falha no plano B grava `consulta_lenta` tipo **`dlcs_falha`**, separado de `dlcs`: não conta como consultado, o jogo volta na próxima rodada; o sucesso apaga a marca.
- **Preço base não é o pacote mais barato.** HITMAN World of Assassination vende a "Part One" (R$ 8,89) no mesmo app. `steam._edicao_base` prefere o pacote com o mesmo nome do app; pacotes menores viram `papel='parcial'` e não servem para "completar".
- Pacote de **R$ 0 em jogo pago** é teste/fim de semana grátis: ignorado (`_edicoes`).
- `GetItems` não lista as DLCs de uma edição; o conteúdo vem de `packagedetails`. Às vezes nem lá → o usuário define com `radar.py conteudo` (`meta.edicoes_manuais`).
- A wishlist e o SteamID saem do perfil público, **sem chave** (XML `?xml=1`). Chave da Steam é opcional.
- **`franchises` da Steam às vezes é editora ou serviço** (medido no banco do dono em 08/10: "EA Play" junta Mass Effect e Need for Speed; "WB Games" junta Batman e LEGO; também "Team17 Digital", "Bandai Namco Entertainment", "Gamirror Games"). `series._editora` descarta serviços conhecidos e nomes que terminam em Games/Digital/Entertainment/Interactive/Studios/Publishing/Software/Inc/Ltd ("Team Ladybug" vai pelo nome exato: um prefixo "Team" apagaria Team Fortress). O resto (Final Fantasy, Total War, Ys, Sonic...) é franquia de verdade. O que escapar, o dono troca à mão na ficha.
- **HLTB do Augmented Steam vem em minutos** (FF VII Remake: 1935 = 32 h, como no site). `GetPlayerAchievements` de jogo sem conquistas responde **400 "no stats"**: vira `{feitas: 0, total: 0}`, não erro.

### IsThereAnyDeal / GG.deals
- **`games/history/v2` vem na moeda da loja; `games/prices/v3` vem convertido (10/10, 0.18.1).** Com `country=BR`, o histórico de Humble, Fanatical, GamesPlanet (EUR, GBP e USD), IndieGala, WinGameStore, PlanetPlay, PlayerLand, ZOOM, DLGamer, JoyBuggy e Zapagames chegava em US$/€/£ (`price.currency`) e `itad.historico` lia como reais: o "menor preço" dessas lojas ficava ~5x abaixo (US$ 3,99 = "R$ 3,99") e o gráfico mentia. AllYouPlay e Playsum misturam moedas no mesmo histórico: sempre ler `currency` por registro, nunca por loja. `cambio.py` converte pela taxa do dia (Frankfurter, `dados/cambio.json`, 24 h; sem rede, a última ou `FALLBACK`; moeda sem taxa = registro descartado). Migração `esquema` 3 manda baixar o histórico de novo (`historico_importado` apagado; `promo_estado.baixado = BAIXADO_ANTIGO` refaz o jogo inteiro na próxima rodada/ficha). Sintoma que denunciou: 65 Selos de uma vez, "menor anterior R$ 38,89 há 29 meses" num jogo que já custou R$ 5,99.
- **Jogo novo na lista não espera o catálogo (0.18.1):** `coleta.atualizar` lê agora os detalhes de quem está em `wl` sem `jogo.nome` (uma tentativa por dia, `consulta_lenta` tipo `nome`); antes o alerta saía com o appid no lugar do nome e sem capa até a próxima leitura (`intervalos_minutos.steam`, 3 h).
- ITAD manda horário com fuso (+02:00). Tudo é convertido para **UTC** antes de gravar; a ordenação é por texto.
- Na ITAD a **mesma loja pode vir 2x** (edições diferentes). `itad.precos` fica com uma por loja: a mais barata com DRM Steam.
- A oferta da **própria Steam vem sem DRM** na ITAD; é tratada como DRM Steam. Em outras lojas, DRM vazio = desconhecido.
- O **"preço atual" sai de `oferta_atual`**, nunca do último registro do histórico (ARK aparecia "grátis" por um brinde de 2022 de uma loja que parou de vender).
- Histórico importado é de **todas as lojas** (mesmo custo); o config só decide quais alertam.
- GG.deals lê a edição parcial em jogos como HITMAN → seus números são ignorados nesses jogos.
- **Aviso de keyshop desligado por padrão (07/10/2026, 0.16).** No banco do dono, 22 dos 26 avisos enviados eram "Keyshop (GG.deals)": Half-Life, HL2, CS:Source e Opposing Force a R$ 7–9 avisando de novo a cada queda de centavos (o `preco_maximo` de R$ 10 pega qualquer clássico barato, e o "menor histórico" é o da própria GG.deals, que desce aos poucos). A GG.deals fica só como informação (ficha, flag e filtro de keyshop). Migração `keyshop_alerta_off` desliga também em quem já tinha o config.
- Não usar várias chaves da mesma API para driblar limite (termos de uso).
