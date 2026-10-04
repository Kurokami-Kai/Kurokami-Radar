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
- **Selo Kurokami** = no piso + Raro ou melhor + ≥ 12 meses de histórico. Um jogo a R$ 10 todo mês não ganha Selo.
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
