# Spec 09 — Biblioteca nova: Coleção por franquias, ficha estilo PlayStation

Status: **Etapa 1 feita** (08/10; vai na 0.17.0); **Etapa 2 decidida (09/10, opção H2): pronta para implementar**; Etapa 3 em discussão. Absorve a [spec 03](03-franquias-com-capas.md).

## Etapas
1. **Ficha nova (decidida: B+ com fundo de captura de tela).** **A referência visual é a amostra B+ de [09-amostras-ficha.html](09-amostras-ficha.html)** (dono: "ficou perfeito"): siga o layout, as medidas e os blocos dela. Inclui: a mesma ficha em Ofertas, Promoções e Biblioteca; arte da biblioteca (`logo.png`, capa vertical do `capa_v`) e captura de tela de fundo (`appdetails.screenshots`, cache); fileira de 5 números; fileira da franquia com setas (só com os jogos que o Radar já conhece: biblioteca e lista); duas colunas (veredito/pisos/histórico | preço por loja, HLTB, crítica, informações); HLTB, jogadores e notas pelo Augmented Steam (servidor, cache de 30 dias, sem chamar em lote); tempo jogado e última vez pelo `GetOwnedGames` (`include_appinfo`/`playtime_forever`, `rtime_last_played`); "trocar" franquia à mão. Conquistas (`GetPlayerAchievements`) podem ficar para o fim da etapa, se pesar.
2. **Biblioteca e Completar (decidida, opção H2).** Leia a seção "Etapa 2: veredito" logo abaixo e abra a referência [09-referencia-biblioteca.html](09-referencia-biblioteca.html).
3. **Franquia inteira** (jogos que não estão na biblioteca nem na lista, em preto e branco): medir a fonte antes. · Skills: `editar-painel`, `coleta-e-apis`, `testar-sem-rede`

## Etapa 2: veredito (09/10) — o que implementar
**Referência visual: [09-referencia-biblioteca.html](09-referencia-biblioteca.html)** (abre no navegador; dados de exemplo: parte da biblioteca do dono, tempos e totais sintéticos). Siga o layout, as medidas e o comportamento dela. A mesma página com todos os dados reais fica só na máquina do dono, em `dados/amostras-biblioteca-escolhida.html` (pasta ignorada pelo Git). As rodadas A–H1 abaixo são histórico.

**Menu e páginas**
- Topo: **Biblioteca ▾** com **Biblioteca** (atalho 1), **Completar** (2) e o link "DLCs dos meus jogos em promoção ↗" (abre Promoções com Tipo DLC + Tenho o jogo base). A aba "DLCs em promoção" sai.
- **Biblioteca** abre na **Coleção**; o botão onde ficava Capas/Texto alterna **▦ Coleção / ☰ Franquias** (tecla T). São a mesma coisa vista de dois jeitos.
  - **Coleção:** vitrine de capas verticais um pouco maiores que a grade de jogos (`minmax(172px,1fr)`); **uma capa por franquia, em pilha** (duas folhas atrás), com "N de M" no canto, barra de progresso no pé, nome e "X h jogadas · faltam N" embaixo. A capa da franquia é a do jogo mais jogado dela. Jogos sem franquia (avulsos) entram na mesma vitrine, sem pilha. Ordem em botões de um clique: Mais jogadas · Recentes · A–Z · Mais completas · Maiores.
  - **Franquias:** 2 prateleiras por linha: nome, "N de M · faltam R$ · X h", barra e a fileira de capas (tenho = colorida com ✓; falta = P&B com preço, + e ♥ se estiver na lista). Ordem: Mais completas · Mais faltando · Mais barato de fechar · Mais jogadas · A–Z.
  - Clique (ou Enter) numa franquia abre a **ficha da franquia em tela cheia**; num avulso, a ficha do jogo (Etapa 1).
- **Completar** alterna **≡ Texto / ▦ Capas**; **abre em Capas, na ordem "Em promoção"**.
  - **Capas:** 3 por linha; capa vertical do jogo, nome, "tem X de Y · faltam R$ · N em promoção", barra e 6 DLCs (header em P&B, colorida ao passar o mouse, % de desconto, preço; a 6ª vira "+ N" se houver mais). Clique abre a **ficha de completar** em tela cheia: capa do jogo, 5 números (faltam, hoje, nos pisos, em promoção, mais barata), "Pôr todas" / "Pôr só as em promoção" / "Abrir a ficha do jogo" e as DLCs agrupadas por tipo (História, Conteúdo, Pacote, Extra...).
  - **Texto:** blocos de franquia **de altura fixa** (sempre 6 linhas; as que sobram ficam em branco), 3 por linha, **só das franquias com algo faltando**, o que falta primeiro: nome do jogo **em lilás** quando falta (♥, % e preço), claro quando tem (✓ e tempo jogado); rodapé "+ N jogos · abrir a franquia ›". Ordem: Em promoção · Mais perto de fechar · Mais barato de fechar · Mais faltando · A–Z.
  - **Não mostrar DLCs inúteis** (cosméticos, trilhas, vozes, cores, skins): o Completar já usa `ctx.relevantes` (tira o que o `dlc.py` classifica como cosmético/atalho, conforme o config), **mas o classificador deixa passar**. Medido em 09/10 no banco do dono: das 1.885 DLCs "conteúdo" do Completar, **72 têm cara de cosmético** — 22 "System Voice"/vozes e 8 "Character Color" (Guilty Gear), 13 trilhas ("Music for The Long Dark", "Promotion Music", BGM), 17 "Pacote Pro"/operadores de Call of Duty (skins), e os trajes/títulos do Devil May Cry 5 ("Alt Hero", "Alt Style", "Alt Title"). **Antes de implementar o Completar, corrigir a classificação em `dlc.py`** (palavras como voice, color/colour, music/soundtrack/OST/BGM, costume/outfit/skin, "Pacote Pro", operator, "Alt ..."), medir de novo e conferir que expansões de verdade (ex.: "Ghost Recon Wildlands - Narco Road", "Sniper Ghost Warrior 2: Siberian Strike") continuam.
- **Texto em geral:** nunca em alvenaria (colunas de alturas diferentes): sempre grade de blocos iguais. Nomes: tenho = claro (`#e8f1f8`), falta = lilás (`#c9a0ff`).

**Ficha da franquia (H2)**
- Tela cheia por cima da página (`#000d` atrás), ✕ e setas ‹ › fixas nas laterais para a franquia anterior/próxima (← →); Esc fecha.
- **Topo:** a **capa horizontal da loja** (`header.jpg`/`capa` do banco, 340 px) à esquerda; à direita etiquetas (Franquia · "✓ completa · tenho N de M" · "♥ N na lista de desejos"), o nome grande, "De AAAA a AAAA · N jogos que o Radar conhece · jogou por último X (há Y)" e as ações (Pôr os N que faltam no carrinho · Trocar a imagem · Juntar / separar). **Fundo:** o `library_hero` do jogo representante **na largura da ficha, na proporção dele** (`background-size:100% auto`), esmaecido. Sem capa vertical no topo (disputava com as capas dos jogos).
- **Jogos da franquia:** título + "N de M · em ordem de lançamento" + **barra de progresso ocupando o resto da linha**. Uma **fileira só, sem setas: arrasta segurando o botão esquerdo** (o clique que termina um arrasto não abre nada; bordas esmaecidas indicam que há mais). As capas crescem de 116 até 156 px e ficam **centralizadas** (`justify-content: safe center`); legenda com nome em 2 linhas e "ano · tempo" (tenho) ou "ano · preço" (falta).
- **Barra de baixo, de ponta a ponta e até o fim da ficha** (fundo `#0e141bf2`, 4 colunas): Números (Jogos N de M %, Tempo jogado, Para completar, DLCs que faltam, Valor cheio · hoje — cada um numa linha) · Onde foi o seu tempo (5 barras) · O que falta (5, com %, preço e +) · Nunca jogados (etiquetas).
- Medido: de 751 a 776 px de altura em 1280×900 (FINAL FANTASY com 30 jogos, GTA, Spider-Man, Resident Evil): cabe sem rolar.

**Teclado e mouse** (uma mão no teclado, outra no mouse): setas andam pelas capas, Enter abre, Esc fecha, letra pula para a primeira com aquela inicial, índice **A–Z** fixo à direita (sem rolar nem digitar), `/` busca, 1/2 trocam a página, T alterna a visualização; barra de atalhos no rodapé.

**Dados:** franquias de `series.franquias` (com `franquia_manual`), tempo jogado de `tempo_jogo`; o que falta numa franquia ainda é só o que está na lista de desejos (a franquia inteira é a Etapa 3).

## Etapa 1: como ficou (08/10)
- `/api/jogo` traz a fileira (`franquia`) e o tempo jogado; `/api/jogo_extra` traz descrição/captura, HLTB/notas e conquistas (cache em `ficha_cache`), e a ficha redesenha quando chega.
- Franquia automática: a da Steam menos serviços e editoras (medido: EA Play, WB Games, Team17 Digital, Bandai Namco Entertainment), com herança pelo nome; "trocar" grava em `franquia_manual`. No banco do dono: 199 franquias com 2+ jogos, FINAL FANTASY com 30.
- Conquistas: só "N de M" e o anel (as mais raras precisariam de mais uma chamada: ficou de fora).
- **Ainda não:** o "Ver a franquia inteira ›" (depende da Etapa 2), e a Biblioteca (Coleção/Franquias) ainda agrupa só pelo nome; a Etapa 2 passa a usar `series.franquias`.

## Etapa 2: três opções para escolher (09/10)
Amostra com os dados reais do dono em `dados/amostras-biblioteca.html` (pasta ignorada pelo Git: biblioteca, lista e tempo jogado são pessoais). Em todas: menu **Biblioteca ▾** no topo (Coleção · Franquias · Completar · "DLCs dos meus jogos em promoção ↗", que abre Promoções com Tipo DLC + Tenho o jogo base) e a barra de Promoções (busca, Ordenar, ≡ Texto / ▦ Capas).
- **A · Três páginas separadas:** Coleção = só o que tenho (grade de capas com tempo jogado; texto = tabela com tempo, última vez, lançamento); Franquias = prateleiras com setas, o que falta em P&B com preço e ♥; Completar = jogo + fileira das DLCs que faltam. Totais só na Coleção; barra de progresso em Completar.
- **B · Coleção por franquia (pedido original):** Coleção = seções por franquia com capas quebrando linha, P&B no meio, "Avulsos" no fim; texto = tabela agrupada por franquia. Franquias e Completar = blocos lado a lado que abrem ao clicar (ocupam a linha inteira).
- **C · Lista lateral (cliente Steam):** lista à esquerda, conteúdo à direita. Coleção filtra por Todos/Jogados recentemente/Nunca jogados/Sem franquia/uma franquia; Franquias e Completar mostram a escolhida com a arte `library_hero` no topo.
- Medido nos dados: 634 jogos, 757 na lista, 135 franquias com algo que tenho (197 com 2+ jogos conhecidos), 278 jogos com DLC faltando. **DLCs possuídas = 0** porque falta o `userdata.json` (a extensão ainda não sincronizou): sem ele, Completar mostra todas as DLCs como faltando.

## Retorno do dono sobre A/B/C (09/10)
- **Coleção:** jogos lado a lado vira "mistura heterogênea" com qualquer filtro. Quer **uma capa por franquia** (um pouco maior que a da grade de jogos) e, ao abrir, uma **ficha da franquia espelhando a ficha B+ do jogo**. Texto do A: não gostou. B (seções por franquia) muito legal, mas com espaço vazio: franquias **2 ou 3 por linha**. C: gostou de "puxar as franquias", mas a barra de rolagem é péssima e digitar no dia a dia não serve. **Regra de layout: uma mão no teclado e outra no mouse; andar pela tela tem de ser prático e bonito; é vitrine, orgulho do jogador.** Ordenação em lista suspensa e os filtros do C não agradaram.
- **Franquias:** prateleiras do A legais (uma por linha, em dúvida). Texto do A bom, mas o nome do jogo precisa de cor que diferencie, e **bug**: abrir um bloco da 2ª ou 3ª coluna deixava buracos na grade (o bloco aberto pulava de linha). Capas do B muito boas; ao clicar, maximizar na tela seguindo a ficha.
- **Completar:** capas do A boas, mas com espaço sobrando (2 ou 3 por linha). Texto do B cansativo.
- **Nome errado da franquia do The Last of Us** ("45527500"): a Steam manda `The Last of Us Franchise|45527500` e no empate a regra ficava com o mais curto. Corrigido em `series._limpa` (ignora nome só com dígitos e tira " Franchise").

## Segunda rodada: D e E (09/10)
Amostra em `dados/amostras-biblioteca-2.html` (mesmos dados). Nas duas: capa da franquia em **pilha** (capa do jogo mais jogado, "23 de 30" e barra de progresso), **ordem em botões de um clique** (sem lista suspensa), **índice A–Z** fixo à direita (sem rolar nem digitar), **atalhos** (setas andam pelas capas, Enter abre, Esc fecha, letra pula, `/` busca, 1/2/3 trocam a página, T alterna texto/capas), **ficha da franquia** no molde da B+ (capa, nome, etiquetas, 5 números: jogos, tempo jogado, para completar, DLCs que faltam, valor; ações; todos os jogos em capas; "onde foi o seu tempo" e "o que falta"). Texto em colunas (sem buraco ao abrir) e nomes coloridos: tenho = claro, falta = lilás.
- **D · Vitrine + ficha em tela cheia:** franquias e avulsos misturados na mesma vitrine; a ficha da franquia abre por cima, com ‹ › (← →) para a vizinha. Franquias e Completar em 3 por linha.
- **E · Estante que abre no lugar:** franquias primeiro, avulsos embaixo em capas menores; a ficha da franquia abre embaixo da linha clicada (com "abrir em tela cheia"). Franquias em 2 prateleiras com setas por linha; Completar em 2 por linha.

## Retorno sobre D/E e terceira rodada: F e G (09/10)
- Dono: abrir **em tela cheia** (D) é melhor que abrir no lugar (E: clica e ainda tem de rolar). **Franquias: 2 por linha como na E, abrindo em tela cheia como na D.** Completar: entre D (pouca informação) e E (muita), sempre abrindo em tela cheia. Ficha da franquia: os jogos empurravam as informações para baixo (FINAL FANTASY) ou cortavam o texto com "…" (Spider-Man). **Telas de texto assimétricas (alvenaria) ficam ruins de ver.**
- Amostra em `dados/amostras-biblioteca-3.html`. Nas duas: Coleção da D (vitrine em pilha); Franquias com 2 prateleiras por linha; Completar abre a **ficha de completar** em tela cheia (jogo, 5 números, DLCs agrupadas por tipo, "pôr todas" / "só as em promoção"); **texto em blocos de altura fixa** (sempre N linhas; as que sobram ficam em branco; "+ N · abrir ›" no rodapé); números da ficha sem corte (o texto de baixo quebra linha).
- **F · Ficha numa tela só:** cabeçalho com os 5 números, jogos numa fileira com setas (os 30 do FINAL FANTASY cabem) e logo abaixo três caixas (onde foi o seu tempo, nunca jogados, o que falta): 864 px de altura, cabe numa tela de 900. Completar em 3 por linha com 6 DLCs.
- **G · Ficha com painel ao lado:** jogos em grade à esquerda (todos visíveis) e um painel fixo à direita com os números, o tempo e o que falta, que acompanha a rolagem. Completar em 2 por linha com 8 DLCs.

## Quase veredito: quarta rodada, H e G (09/10)
- Dono: ficha F "com ressalvas"; o painel lateral da G tem de ir **até o fim** da ficha; quer uma versão com esse painel **na horizontal, embaixo dos jogos**; os jogos numa fileira só, **sem setas: arrastar segurando o botão esquerdo**. "Basicamente o layout do F, mas com a barra vertical do G na horizontal."
- **Coleção e Franquias são a mesma coisa:** o menu vira **Biblioteca** (abre na Coleção, a vitrine de capas em pilha) e o botão onde ficava Capas/Texto alterna **Coleção / Franquias** (2 prateleiras por linha, de arrastar). **Completar** fica com Texto (blocos de altura fixa) e Capas (3 por linha, 6 DLCs), da F, e abre a ficha de completar em tela cheia.
- Amostra em `dados/amostras-biblioteca-4.html`. **H:** cabeçalho da G (capa, etiquetas, nome, ações), fileira de arrastar com bordas esmaecidas indicando que há mais, e a barra deitada de ponta a ponta até o fim (números | onde foi o seu tempo | o que falta | nunca jogados): 814–846 px de altura, cabe numa tela de 900. **G:** igual, mas com o painel ao lado indo até o fim (o conteúdo acompanha a rolagem).
- A confirmar: o "texto" do Completar já usa o mesmo bloco da Coleção em texto da F; se a ideia era o Completar em texto mostrar as **franquias com os jogos que faltam** (e não as DLCs), é uma troca pequena.

## Quinta rodada: H1 e H2 (09/10)
- Dono escolheu a **H com ressalvas**: a barra verde ao lado de "Jogos da franquia" não lia como 100% (era curta); os jogos não chegavam às bordas nem ficavam centralizados; o fundo parecia desproporcional (banner esticado/ampliado); a capa vertical do topo disputava com as capas dos jogos. Pediu para testar uma **capa horizontal**.
- **Completar decidido:** Texto = o bloco de franquia da Coleção em texto da F (o que falta em lilás), só das franquias com algo faltando e o que falta primeiro; clique abre a ficha da franquia. **Capas = DLCs (3 por linha, 6 DLCs), abrindo na ordem "Em promoção".**
- Amostra em `dados/amostras-biblioteca-5.html`. Nas duas: barra de progresso ocupando o resto da linha; jogos crescem até 156 px e ficam centralizados (com muitos, arrasta); números da barra de baixo numa linha só.
- **H1 · Banner horizontal:** `library_hero` no topo, na proporção dele (até 260 px de altura, corta um pouco em cima e embaixo, não estica), nome e ações sobre o banner. 838–863 px de altura.
- **H2 · Capa horizontal ao lado do nome:** a capa da loja (`header.jpg`, 340 px) à esquerda do nome e das ações; o banner fica só de fundo esmaecido, na largura da ficha. 751–776 px.

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
