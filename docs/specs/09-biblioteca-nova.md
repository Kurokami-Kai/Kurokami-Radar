# Spec 09 — Biblioteca nova: Coleção por franquias, ficha estilo PlayStation

Status: **em discussão** (rascunho de 08/10, respostas do dono na mesma noite; absorve a [spec 03](03-franquias-com-capas.md)) · Skills: `editar-painel`, `coleta-e-apis`, `testar-sem-rede`

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
- **Três amostras para escolher:** [09-amostras-ficha.html](09-amostras-ficha.html) (abre no navegador; A = biblioteca da Steam, banner largo e coluna lateral; B = PlayStation, capa vertical e fundo do banner, sequências logo abaixo e abas; C = cartões, faixa curta do banner e blocos em grade). Cada uma nos dois estados.

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
- Ver antes um esboço visual dos dois modos (blocos de texto × capas) e da ficha, para decidir o layout?

## Aceite (a fechar depois da discussão)
- Coleção abre por padrão, por franquia, com capas; alterna Capas/Texto e lembra a escolha.
- Capas que tenho coloridas com ✓; que faltam em cinza com preço e +; legível em capas P&B.
- Ficha com capa, descrição, sequências e tempo jogado; funciona no celular.
