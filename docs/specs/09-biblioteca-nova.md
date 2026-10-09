# Spec 09 — Biblioteca nova: Coleção por franquias, ficha estilo PlayStation

Status: **Etapa 1 pronta para implementar** (ficha decidida em 08/10); Etapas 2 e 3 ainda em discussão. Absorve a [spec 03](03-franquias-com-capas.md).

## Etapas
1. **Ficha nova (decidida: B+ com fundo de captura de tela).** **A referência visual é a amostra B+ de [09-amostras-ficha.html](09-amostras-ficha.html)** (dono: "ficou perfeito"): siga o layout, as medidas e os blocos dela. Inclui: a mesma ficha em Ofertas, Promoções e Biblioteca; arte da biblioteca (`logo.png`, capa vertical do `capa_v`) e captura de tela de fundo (`appdetails.screenshots`, cache); fileira de 5 números; fileira da franquia com setas (só com os jogos que o Radar já conhece: biblioteca e lista); duas colunas (veredito/pisos/histórico | preço por loja, HLTB, crítica, informações); HLTB, jogadores e notas pelo Augmented Steam (servidor, cache de 30 dias, sem chamar em lote); tempo jogado e última vez pelo `GetOwnedGames` (`include_appinfo`/`playtime_forever`, `rtime_last_played`); "trocar" franquia à mão. Conquistas (`GetPlayerAchievements`) podem ficar para o fim da etapa, se pesar.
2. **Biblioteca: Coleção, Franquias e Completar** com os modos Capas e Texto; DLCs em promoção sai. Precisa de amostras antes (como as da ficha).
3. **Franquia inteira** (jogos que não estão na biblioteca nem na lista, em preto e branco): medir a fonte antes. · Skills: `editar-painel`, `coleta-e-apis`, `testar-sem-rede`

## Pedido (dono, 08/10)
- A aba está mal disposta. Hoje: **Completar · Franquias · Coleção · DLCs em promoção** (botões no topo da aba).
- Deve ficar parecida com **Ofertas** (menu no topo com subpáginas, talvez).
- **Coleção primeiro**, separada **por franquias, com capas**. Na mesma tela, os jogos da franquia que **não tenho** aparecem em **preto e branco** (o que falta completar). Isso tira a necessidade da aba Franquias como está, mas ela é útil **em texto**: vira o segundo modo de ver.
- **Dois modos de visualização** da Coleção: capas e texto.
- **DLCs em promoção** pode sair, a menos que tenha uma utilidade.
- **Ao clicar num jogo, uma página como a do PlayStation:** capa no canto superior esquerdo, descrição à direita, separada; embaixo, capas menores dos jogos da mesma franquia (sequências); tempo de jogo, tempo para platinar etc.

## Respostas do dono (08/10, noite)
- **Ficha nova em todo o painel**, não só na Biblioteca. O layout de tudo precisa ser pensado a fundo (casa com a spec 08, "layout em etapas").
- **Os dois modos de ver valem para Franquias e Completar** (ainda indeciso entre blocos lado a lado que abrem ao clicar no nome, como o Franquias de hoje, e capas separadas do mesmo jeito): por isso, os dois. Franquias e Completar ficam, com as mudanças. **DLCs em promoção sai.**
- **O que falta aparece em preto e branco esteja ou não na lista de desejos**; os que estão na lista ganham um indicador.
- **Juntar/separar franquias:** aceito qualquer jeito melhor que eu achar (ver proposta abaixo).
- **Tempo para zerar: pelo Augmented Steam** (o dono já usa; o quadro "How Long to Beat" da loja com História principal, + Extras, Completacionista e "Mais informações").

## Ficha padronizada (08/10, noite)
- **A mesma ficha abre em Ofertas, Promoções e Biblioteca**; só mudam os blocos (não tenho: preço, piso, costuma voltar, carrinho; tenho: tempo jogado, última vez, conquistas, DLCs). **HLTB em todos os jogos.**
- **Sem espaço vazio embaixo da imagem** (reclamação sobre a ficha de hoje): usar a arte da biblioteca da Steam, que existe por appid sem chamada extra: `library_hero.jpg` (1920×620), `logo.png` (fundo transparente) e `library_600x900_2x.jpg` (capa vertical), em `shared.fastly.steamstatic.com/store_item_assets/steam/apps/<appid>/` (conferido em 7 jogos, inclusive os de caminho com hash). Falta o que fazer quando não houver hero/logo (cair para `header.jpg` e o nome em texto).
- **HLTB do Augmented Steam vem em minutos** (FF VII Remake: 1935 = 32 h, como no site). A API responde com CORS aberto, mas buscar pelo servidor com cache.
- **Três amostras para escolher:** [09-amostras-ficha.html](09-amostras-ficha.html) (abre no navegador; A = biblioteca da Steam, banner largo e coluna lateral; B = PlayStation, capa vertical e fundo do banner, sequências logo abaixo e abas; C = cartões, faixa curta do banner e blocos em grade). Cada uma nos dois estados. **Escolhida: B+ com fundo de captura de tela** (a "cor da capa" fica só como reserva quando o jogo não tiver captura).

## Escolha da base (08/10, noite): B aprimorada ("B+" nas amostras)
- Dono: gostou da B (PlayStation), mas (1) a imagem repetida atrás é ruim, porque o banner é a mesma arte da capa; (2) a barra de rolagem da fileira da franquia é feia; (3) as informações ficavam menos práticas que na A.
- **B+:** capa vertical à esquerda, logo, etiquetas, descrição de 3 linhas ("mais"), **fileira de 5 números** (sem ter: melhor preço, termina, análises, para zerar, crítica; tendo: tempo jogado, conquistas com anel, para zerar com o seu %, análises, preço na Steam) e ações. **Fundo sem repetir a capa**, duas opções para o dono escolher: captura de tela do jogo escurecida (`appdetails.screenshots`, 1 chamada com cache) ou **cor da capa** (média ponderada pela saturação, num canvas de 24×36; o CDN da Steam manda `Access-Control-Allow-Origin: *`, então dá no navegador).
- **Fileira da franquia sem barra de rolagem:** setas ‹ › nas pontas (somem no começo e no fim), abre centrada no jogo atual, ano embaixo de cada capa, barra "tenho 23 de 30" e "Ver a franquia inteira ›". No celular, arrasta com o dedo.
- **Corpo em duas colunas, como a A:** à esquerda o veredito (tipo de recorde + costuma voltar), menores preços e histórico; ou, tendo, o seu progresso (conquistas, DLCs) e o histórico. À direita, **preço agora por loja** (com keyshop), How Long to Beat (barra com o marcador "você"), crítica e informações.
- Jogos novos guardam a capa vertical em caminho com hash: usar o `capa_v` do banco, não montar a URL.

## Hoje (o que existe)
- `api_biblioteca` (`painel.py`) devolve totais (valor cheio, hoje, piso, para completar), `jogos[]` com `falta[]` (DLCs que faltam) e as séries agrupadas pelo nome (o campo `franquia` da Steam mistura coisas como "EA Play").
- `renderBib` (`painel.html`, seção `biblioteca`): faixa de totais, barra "Progresso da coleção" com o carrinho, e os quatro segmentos com ordenações próprias (`BSORTS`).

## Proposta inicial (para discutir)
1. **Topo:** `Biblioteca ▾` com **Coleção** (abre por padrão), **Franquias** e **Completar**, cada uma com os modos Capas e Texto (a escolha fica salva). Os totais e a barra de progresso ficam no alto da Coleção.
2. **Coleção, modo Capas:** uma seção por franquia (nome, "tenho N de M", recolher/expandir salvo no navegador); capas verticais; as que tenho coloridas com ✓, as que faltam em cinza com o preço de hoje e o **+** do carrinho (o identificador vale para capas que já são P&B). Jogos sem franquia num bloco "Avulsos" no fim.
3. **Coleção, modo Texto:** a atual Franquias, em tabela por série (tenho / falta / preço para completar), mais densa.
4. **Completar:** fica (o "quanto custa fechar as DLCs de cada jogo"), também com Capas e Texto; a ficha nova mostra as DLCs que faltam.
5. **DLCs em promoção sai:** é o mesmo que *Promoções* com "Tenho o jogo base ✓" e Tipo DLC. No lugar, um link "DLCs dos seus jogos em promoção" que abre Promoções com esses filtros.
6. **Ficha estilo PlayStation, em todo o painel:** capa grande à esquerda, à direita nome, descrição curta, avaliações, preço/DLCs; embaixo, faixa de capas menores da mesma franquia em ordem de lançamento; blocos de números.

## Dados: o que dá para ter e o custo
| Dado | Fonte | Custo |
|---|---|---|
| Tempo jogado, última vez que jogou | `GetOwnedGames` (já chamamos; falta pedir `playtime_forever`/`rtime_last_played`) | zero chamadas a mais |
| Conquistas (N de M, "platinado" = 100%) | `ISteamUserStats/GetPlayerAchievements` + esquema do jogo; exige "Detalhes dos jogos" público | 1–2 chamadas por jogo, sob demanda ao abrir a ficha, com cache |
| Descrição curta | `appdetails` da Steam (`short_description`) | 1 chamada por jogo, cache |
| Sequências | as séries que já agrupamos, ordenadas por lançamento | zero |
| Tempo para zerar / completacionista | **API do Augmented Steam** (`https://api.augmentedsteam.com/app/<appid>/v2`, sem chave; a mesma que a extensão usa). Medido em 08/10 com o Until Then: `hltb: {story: 958, extras: 1290, complete: 1686, url}` (minutos? 958 min = 16 h, o HLTB diz 17,3 h: **conferir a unidade em 3 jogos antes**), mais `players` (agora, pico do dia, pico histórico), `reviews.metauser` e `reviews.opencritic`, `family_sharing` | 1 chamada por jogo, só ao abrir a ficha, cache de 30 dias. Serviço de terceiro sem contrato: tolerar falha (a ficha abre sem o quadro) e não chamar em lote |

## Juntar e separar franquias (proposta)
- **Automático primeiro:** a franquia da Steam (`basic_info.franchises`, já guardada em `jogo.franquia`) quando ela for uma franquia de verdade, e o agrupamento por nome (`series.py`) quando ela for uma editora ou um serviço ("EA Play"). Regra a medir: franquia da Steam que cobre jogos de nomes muito diferentes e com muitos itens é editora.
- **À mão, na ficha:** linha "Franquia: Need for Speed [trocar]" com sugestões das franquias que já existem (juntar = escolher uma; separar = digitar um nome novo; "automático" desfaz). Guardado numa tabela nova (`franquia_manual: appid, nome`), que sempre vence o automático.
- **Arrastar capa para outra seção** na Coleção: talvez depois; a ficha resolve o caso comum com menos código.

## O que falta numa franquia (fonte)
- Hoje só se conhecem os jogos da biblioteca e da lista de desejos. Para mostrar **todos** os que faltam em preto e branco, falta uma fonte da franquia inteira. A medir antes de prometer: (1) se a Query da Steam (`IStoreQueryService/Query`) filtra pelo criador da franquia (`franchises[].creator_clan_account_id`), 1 chamada por franquia; (2) se não, a página `store.steampowered.com/franchise/<nome>`. Cache longo (a franquia muda pouco).

## Perguntas em aberto
- "Platinar": vale 100% das conquistas da Steam (`GetPlayerAchievements`), além do "Completacionista" do HLTB?
- Etapa 2: esboço dos dois modos (blocos de texto × capas) antes de programar.

## Aceite (a fechar depois da discussão)
- Coleção abre por padrão, por franquia, com capas; alterna Capas/Texto e lembra a escolha.
- Capas que tenho coloridas com ✓; que faltam em cinza com preço e +; legível em capas P&B.
- Ficha com capa, descrição, sequências e tempo jogado; funciona no celular.
