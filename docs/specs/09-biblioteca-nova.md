# Spec 09 — Biblioteca nova: Coleção por franquias, ficha estilo PlayStation

Status: **em discussão** (rascunho de 08/10; absorve a [spec 03](03-franquias-com-capas.md)) · Skills: `editar-painel`, `coleta-e-apis`, `testar-sem-rede`

## Pedido (dono, 08/10)
- A aba está mal disposta. Hoje: **Completar · Franquias · Coleção · DLCs em promoção** (botões no topo da aba).
- Deve ficar parecida com **Ofertas** (menu no topo com subpáginas, talvez).
- **Coleção primeiro**, separada **por franquias, com capas**. Na mesma tela, os jogos da franquia que **não tenho** aparecem em **preto e branco** (o que falta completar). Isso tira a necessidade da aba Franquias como está, mas ela é útil **em texto**: vira o segundo modo de ver.
- **Dois modos de visualização** da Coleção: capas e texto.
- **DLCs em promoção** pode sair, a menos que tenha uma utilidade.
- **Ao clicar num jogo, uma página como a do PlayStation:** capa no canto superior esquerdo, descrição à direita, separada; embaixo, capas menores dos jogos da mesma franquia (sequências); tempo de jogo, tempo para platinar etc.

## Hoje (o que existe)
- `api_biblioteca` (`painel.py`) devolve totais (valor cheio, hoje, piso, para completar), `jogos[]` com `falta[]` (DLCs que faltam) e as séries agrupadas pelo nome (o campo `franquia` da Steam mistura coisas como "EA Play").
- `renderBib` (`painel.html`, seção `biblioteca`): faixa de totais, barra "Progresso da coleção" com o carrinho, e os quatro segmentos com ordenações próprias (`BSORTS`).

## Proposta inicial (para discutir)
1. **Topo:** `Biblioteca ▾` com **Coleção** (abre por padrão) e **Completar**. Os totais e a barra de progresso ficam no alto da Coleção.
2. **Coleção, modo Capas:** uma seção por franquia (nome, "tenho N de M", recolher/expandir salvo no navegador); capas verticais; as que tenho coloridas com ✓, as que faltam em cinza com o preço de hoje e o **+** do carrinho (o identificador vale para capas que já são P&B). Jogos sem franquia num bloco "Avulsos" no fim.
3. **Coleção, modo Texto:** a atual Franquias, em tabela por série (tenho / falta / preço para completar), mais densa.
4. **Completar:** fica (é o "quanto custa fechar as DLCs de cada jogo"); se a ficha nova mostrar as DLCs que faltam, pode virar só um modo de ordenação da Coleção.
5. **DLCs em promoção sai:** é o mesmo que *Promoções* com "Tenho o jogo base ✓" e Tipo DLC. No lugar, um link "DLCs dos seus jogos em promoção" que abre Promoções com esses filtros.
6. **Ficha estilo PlayStation** (só para jogos da biblioteca, ou para todos?): capa grande à esquerda, à direita nome, descrição curta, avaliações, preço/DLCs; embaixo, faixa de capas menores da mesma franquia em ordem de lançamento; blocos de números.

## Dados: o que dá para ter e o custo
| Dado | Fonte | Custo |
|---|---|---|
| Tempo jogado, última vez que jogou | `GetOwnedGames` (já chamamos; falta pedir `playtime_forever`/`rtime_last_played`) | zero chamadas a mais |
| Conquistas (N de M, "platinado" = 100%) | `ISteamUserStats/GetPlayerAchievements` + esquema do jogo; exige "Detalhes dos jogos" público | 1–2 chamadas por jogo, sob demanda ao abrir a ficha, com cache |
| Descrição curta | `appdetails` da Steam (`short_description`) | 1 chamada por jogo, cache |
| Sequências | as séries que já agrupamos, ordenadas por lançamento | zero |
| Tempo para zerar / platinar | **HowLongToBeat não tem API oficial.** Opções: (a) IGDB "time to beat" (oficial, grátis, exige registrar app na Twitch; cobertura menor); (b) endpoint não oficial do HLTB (quebra quando o site muda); (c) só um link para a página do jogo no HLTB | (a) chave nova no keyring; (b) frágil; (c) zero |

## Perguntas em aberto
- Ficha nova só na Biblioteca, ou substitui a ficha atual em todo o painel?
- Franquia: quem decide o agrupamento quando o nome engana (ex.: "Need for Speed" × "NFS Hot Pursuit Remastered")? Permitir juntar/separar à mão?
- "Platinar": basta 100% das conquistas da Steam? HLTB entra (a, b ou c)?
- O que faltar e não estiver na lista de desejos aparece em cinza também (franquia inteira da Steam) ou só os da lista?

## Aceite (a fechar depois da discussão)
- Coleção abre por padrão, por franquia, com capas; alterna Capas/Texto e lembra a escolha.
- Capas que tenho coloridas com ✓; que faltam em cinza com preço e +; legível em capas P&B.
- Ficha com capa, descrição, sequências e tempo jogado; funciona no celular.
