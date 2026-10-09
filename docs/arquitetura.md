# Arquitetura

Kurokami Hunter é um app **local** de Windows (Python 3.12) que monitora a lista de desejos da Steam em várias lojas, guarda o histórico de preços em SQLite, notifica pela central do Windows e serve um painel web em `http://localhost/kurokami`. Não existe servidor do projeto: cada usuário roda tudo no próprio PC, com as próprias chaves de API.

## Visão geral

```
                    ┌──────────── bandeja.py (pystray, thread principal) ────────────┐
                    │  menu do ícone · tooltip com progresso · verificação de versão  │
                    └──────┬───────────────────────────────┬────────────────────────┘
                           │                               │
             servico.Servico (thread)            painel.py (ThreadingHTTPServer, thread)
             a cada N min: ciclo()               GET/POST /api/*  ·  /kurokami (painel.html)
                           │                               │
   ciclo(): coleta.atualizar → analise.avaliar → notificador.processar → relatorio
                           │
    ┌──────────────┬───────┴────────┬───────────────┐
  steam.py        itad.py        ggdeals.py      (rede.py: HTTP, ritmo, backoff)
                           │
                     banco.py (SQLite em dados/radar.sqlite3)
```

- **Processo único.** A bandeja é o processo principal. O serviço de coleta e o servidor do painel são threads dele. Uma porta-trava (`127.0.0.1:47811`) impede duas cópias.
- **Janelas Tk** (chaves, atualização) rodam em **processo separado** (`KurokamiRadar.exe chaves` / `atualizar-app`), porque o pystray ocupa a thread principal.
- **Notificações**: `notificar.py` monta XML de toast e chama PowerShell (`-EncodedCommand`, janela oculta). O app se registra em `HKCU\Software\Classes\AppUserModelId\Kurokami.Hunter` para aparecer com nome e ícone.

## Fontes de dados e o papel de cada uma

| Fonte | Usada para | Limites conhecidos |
|---|---|---|
| Steam `IStoreBrowseService/GetItems` (sem chave) | catálogo da lista, preços Steam, análises, edições/pacotes, bundles, capas, franquia, fim do desconto | lotes de 50; sem limite publicado |
| Steam `GetWishlist` (sem chave) | lista de desejos e prioridade | perfil precisa ter "Detalhes dos jogos" público |
| Loja Steam (`appdetails`, `packagedetails`) | lista de DLCs de cada jogo; conteúdo das edições | ~200 chamadas / 5 min (ritmo 1,6 s); `GetDLCForApps` exige chave de parceiro, por isso este plano B |
| Steam Web API (chave opcional) | `ResolveVanityURL` (plano B), `GetOwnedGames` (também o tempo jogado e a última vez, para a ficha: `tempo_jogo`) | — |
| `userdata.json` (opcional; a extensão 1.1 grava sozinha, ou manual) | DLCs que o usuário possui, seguidos, ignorados, carrinho da Steam | é um retrato; pela extensão, renova a cada visita à loja (no máximo a cada 10 min) |
| IsThereAnyDeal (chave obrigatória) | preços em ~34 lojas BR (com DRM), histórico (`history/v2`), menor histórico, expiração da oferta | limita ritmo; 200 ids por chamada de preços |
| Steam `IStoreQueryService/Query` (sem chave) | **Steam inteira** (spec 07): todas as promoções, 1.000 por chamada, com preço, pacote, fim, análises, lançamento e capa | `sort: 2` obrigatório (sem ele a paginação repete); só vem o que tem desconto; ~108 chamadas em grande promoção, ~7 num dia comum; gzip (150 KB por página) |
| Ficha do jogo, ao abrir (`ficha.extras`, spec 09) | `appdetails` (descrição, captura de tela de fundo, desenvolvedor, gêneros), **Augmented Steam** (`api.augmentedsteam.com/app/<appid>/v2`, sem chave: HLTB em minutos, jogadores, Metacritic de usuários, OpenCritic) e `GetPlayerAchievements` (conquistas, só de jogo seu, com chave) | 1 chamada de cada por jogo, só ao abrir a ficha, nunca em lote, em paralelo; cache em `ficha_cache` (30 dias; conquistas 6 h). Augmented Steam é serviço de terceiro sem contrato: falhou = ficha sem o quadro |
| GG.deals (chave opcional) | melhor preço oficial e keyshop + mínimos | atualiza 1x/h; não diz a loja; erra em jogos com "edição parcial" |

## Ciclo de coleta (`coleta.atualizar`)

1. Perfil → SteamID (XML público do perfil; API como reserva). Lista de desejos (+ `extras` do config). Biblioteca = `userdata.json` ∪ `GetOwnedGames` ∪ `tenho_manual`.
1b. **Steam inteira** (`steam_inteira.coletar`, a cada `intervalos_minutos.steam_inteira` (60 min), no "Verificar agora" e na completa; `config.steam_inteira`): Query da Steam (~10 s) + marca e menores da ITAD (guardados em `promo_estado`; repedidos quando o preço muda ou após 1 dia; até 20 lotes por rodada, populares primeiro) + avaliação com o histórico que já tem; só então substitui o retrato `steam_promo`. Resposta vazia ou cortada levanta erro e não troca o retrato; falha só vai para o log. Não gera avisos.
2. **Catálogo Steam** (a cada `intervalos_minutos.steam`, ou forçado): detalhes da lista, conteúdo das edições, listas de DLC (plano B pela loja, com orçamento `chamadas_lentas_por_rodada`), bundles e itens de bundles. Se sobrar fila lenta, o catálogo roda de novo no próximo ciclo.
3. **Biblioteca** (1x/dia): detalhes de tudo que o usuário tem + menor histórico na ITAD das DLCs que faltam.
4. **ITAD**: mapeia appid→id ITAD; importa histórico uma vez por jogo (todas as lojas); preços atuais de todas as lojas → `preco` (só quando muda) e `oferta_atual` (snapshot vigente).
5. **GG.deals** (a cada 60 min).
6. **Custo completo** dos jogos em modo "completo" vira uma "loja" própria no histórico (`Completo (Steam)`).
7. **Histórico da Steam inteira** (etapa 6 no código; `steam_inteira.historicos`, toda rodada com chave da ITAD): de quem está perto do recorde (marca N/H/S ou preço ≤ menor de 1 ano), `steam_inteira_hist_por_rodada` (60) jogos por vez — novos recordes, jogos e os mais avaliados primeiro — nas lojas marcadas, em `promo_hist`; no primeiro 429 da ITAD (cota ~100 chamadas em 5 min) para e segue na próxima. Depois reavalia o retrato (`aval`).

Verificação **rápida** = o ciclo normal (respeita intervalos e orçamento). **Completa** = `forcar=True, sem_limite=True`; a primeira é sempre completa, depois a cada `verificacao_completa_dias`.

## Avaliação (`analise.avaliar`)

Por jogo da lista (exceto os que o usuário já tem): para cada oferta das **lojas marcadas** (e DRM Steam, se exigido) roda `analise.analisar(linhas, preco, corte)`:
- `linha_do_tempo` junta o histórico das lojas marcadas em trechos (menor preço, corte do menor, maior corte); `episodios` vira promoções (intervalo sem desconto < 1 dia não separa).
- **Raridade** (eixo 1): episódios anteriores com corte ≥ atual − 5, por ano, nos últimos 24 meses. Comum ≥ 3/ano · Incomum 1,5–3 · Raro 0,75–1,5 · Ultrarraro < 0,75 · Lendário = nunca (histórico inteiro), com ≥ 24 meses de histórico e ≥ 1 promoção anterior; 12–24 meses: no máximo Ultrarraro. Sem promoção anterior nas lojas marcadas ou histórico < 6 meses: no máximo Incomum.
- A raridade não aparece mais nas telas (0.15): vira a coluna informativa **"Costuma voltar"** (`costuma_voltar`: histórico curto · primeira promoção · nunca teve esse desconto (histórico inteiro) · não teve nos últimos 2 anos · todo mês · a cada ~N meses · 1 vez por ano · 1 vez em 2 anos; `dica_volta` dá a linha "Nos últimos 2 anos: N vezes com -Y% ou mais…").
- **No piso** (eixo 2): corte ≥ maior corte da vida − 5, ou preço ≤ menor de 24 meses + 1%.
- **Tipo de preço** (reais): compara com o menor preço *antes* do episódio de preço atual (`piso_ref`, o menor de sempre): `piso_tipo` novo / raro (≥ 18 meses sem esse nível ou ≤ 50% do recorde) / igual / 24m (igual ao menor dos últimos 24 meses).
- **Selo Kurokami (0.15)** = só G: `piso_tipo == "raro"` + ≥ 1 promoção anterior nas lojas marcadas + corte ≥ `selo_corte_minimo`. `selo_motivo`: "preço caiu pela metade ou mais (o menor anterior era R$ X, mm/aaaa)" ou "o menor preço anterior (R$ X) foi há N meses". O Lendário (F) não dá mais Selo (escada de descontos; ver `decisoes.md`).
  - *Frase para os textos do usuário (referência):* "o menor preço em muito tempo: o recorde anterior tem 1,5 ano ou mais, ou o preço caiu pela metade".
- `tipos_de(an)` = lista não exclusiva: `selo` se Selo; `novo` se `piso_tipo` novo ou raro; `igual`; `24m`. `tipo_oferta` = o primeiro de [selo, novo, igual, 24m] (vitrine, "Mostrar só", título do aviso).
- **Score** fica só interno (corte × peso da raridade + 10 no piso). Análises não entram em nada.

**Avisa** (`avisa_por`) se algum tipo da oferta está ligado em `alerta.tipos` e (é o Selo, que já tem o `selo_corte_minimo`, ou corte ≥ `desconto_minimo`). Raridade e favoritos não decidem nada. Motivo por tipo (`motivo_tipo`). Modo completo e keyshop têm regras próprias. Saída agrupada: um alerta por jogo, na ordem selo, novo, igual, 24m e, dentro de cada, maior corte (`chave_aviso`).

**Régua da Steam** (`regua_steam`): só informativa. Se a Steam sozinha ("Steam (direto)" + Steam da ITAD) dá Novo recorde ou Selo e as lojas marcadas não, a ficha diz "Na Steam, é o menor preço já registrado. Nas suas lojas, <loja> já teve R$ X (mm/aaaa)." (`menor_anterior` acha o registro que impediu).

## Notificação (`notificador.Notificador`)

Linha de base na primeira vez (não dispara nada em massa) → ao **ligar um tipo** (`meta.tipos_ligados` muda), quem já estava assim e só avisaria por ele entra em `notificado` sem toast e sai um resumo "<Tipo> ligado: N jogos já estão assim agora…" com "Ver" (abre `#vale`) → avisa novidades, quedas ≥ `melhora_minima_reais` e jogos que "rearmaram" (saíram e voltaram). Respeita pausa, horário de silêncio (guarda pendentes), máximo por rodada (resto vira resumo) e silenciados. Avisos de "termina em breve" para carrinho/o que avisa. Título por tipo ("SELO KUROKAMI · …", "Novo recorde · …", "Igual ao recorde · …", "Menor em 2 anos · …"), nunca por raridade.

## Painel

`painel.html` é um SPA único (sem build), visual da loja Steam. O HTML fica em `painel.html` e o CSS/JS em `radar/painel-web/`, um arquivo por seção; a cada `GET /kurokami` o `montar_painel()` troca cada `/*incluir x*/` pelo arquivo, e o navegador recebe uma página só, com um `<style>` e um `<script>` (mesmo escopo, na ordem das marcas; sem cache velho de JS depois de atualizar). Lê tudo via `/api/*` (ver `api.md`). Topo: **Ofertas ▾** (Destaques, Promoções, Lista de desejos: as páginas novas, abaixo; e a Tabela com todos os filtros), **Biblioteca ▾** (Biblioteca, Completar), **Configurações ▾** (Configurações, Notificações), Carrinho e o avatar da Steam no canto (`/api/resumo` → `perfil`). Abas: **Ofertas** (`#vale`) e **Biblioteca** (`#bib`) = as páginas novas num iframe (abaixo); **Tabela com todos os filtros** (`#lista`) = o explorador com filtros **no servidor** (`/api/promocoes`, pensando na Steam inteira, spec 07; abre com `P_PADRAO`); `/api/vitrine` ficou só para o "N na vitrine" do topo; Carrinho, Notificações, Configurações ("O que te avisa"). O endereço guarda a aba (`#vale`, `#lista`…).

**Steam inteira na aba Promoções** (o painel sempre pede `fonte: "steam"`; o filtro "Na lista de desejos" separa a lista): às linhas da lista somam-se `LinhaSteam` leves (de `steam_promo`, com a avaliação de `aval`: tipos, Selo, piso_ref, Costuma voltar; sem quem já está na lista; `__slots__`, ~50 MB com 108 mil), refeitas quando há coleta nova; a relação (tenho, carrinho, seguido, ignorado) é refeita junto com o cache da lista. Os mesmos filtros servem às duas (campo que a linha leve não tem vale None). A ordenação é por ordenações estáveis, do último critério ao primeiro (o `cmp_to_key` levava segundos). Medido: ~150–300 ms com 108 mil itens e cache quente; ~3,5 s na primeira vez. Linha de fora da lista abre a ficha (`/api/jogo` → `_jogo_steam`: histórico das lojas marcadas baixado na hora, avaliação igual à da lista, botão Monitorar); o + põe no carrinho e monitora. +18 = descritores de conteúdo 3 ou 4 da Steam (`steam_promo.adulto`), oculto se o filtro `adulto` não vier.

**Ficha do jogo** (spec 09, amostra B+ de `docs/specs/09-amostras-ficha.html`): a mesma em Ofertas, Promoções e Biblioteca (`abrirJogo` → `renderModal`), só mudam os blocos se você tem o jogo. `/api/jogo` traz o que é local (preços, avaliação, DLCs, fileira da franquia e tempo jogado) e a ficha abre na hora; `/api/jogo_extra` vem em paralelo e redesenha quando chega (descrição, captura de fundo, HLTB, notas, conquistas). Arte por appid no CDN da Steam, sem chamada: `logo.png` (sem ele, o nome em texto) e a capa vertical (`capa_v` do banco, senão `library_600x900_2x.jpg`, senão a horizontal inteira). Sem captura de tela, o fundo é a cor da capa (média pela saturação num canvas de 24×36). **Franquia** (`series.franquias`): a da Steam (`jogo.franquia`), menos serviços e editoras ("EA Play", "WB Games", "Team17 Digital"...: `series._editora`); com várias, a de mais jogos conhecidos; sem ela, o agrupamento pelo nome, que herda a da Steam dos outros do grupo; a troca à mão (`franquia_manual`) sempre vence. A fileira só mostra os jogos da biblioteca e da lista. **Painéis** (`fxListaAbas` → `fxAbas`, `fxPainel`, `fxAba`): `fxVale` (+ `fxPisos`), `fxHist` (+ `desenharGrafico`: `fxEnvelope` e `fxFaixa`), `fxLojas` (+ `fxCaminhos`), `fxFileira` (só com franquia de 2+ jogos) e `fxSobre` (+ `fxDlcs`); `MABA` guarda a parte aberta; trocar de parte redesenha só `#fxPainel` (e o gráfico/fileira); `renderModal` guarda a rolagem do painel.

**Cache das linhas** (`painel.linhas_promocoes`): uma linha por jogo da lista, montada em ~0,5 s e guardada em memória com trava; filtrar/ordenar nele custa milissegundos. É refeito quando termina uma coleta (`servico.ciclo`), em qualquer POST do painel, quando o config ou o `userdata.json` muda (assinatura) e, por segurança, a cada 10 min. `/api/lista` também usa o cache. Seguidos/ignorados vêm de `conta_steam.relacao` (único leitor do `userdata.json` para isso). Localhost sempre liberado; outros aparelhos só com PIN (cookie `kr`) e se `painel.rede_local` estiver ligado. Porta 80 com reserva na 8787.

**Ofertas e Biblioteca (0.17, spec 09):** são páginas próprias, `radar/ofertas.html` (amostra 8) e `radar/biblioteca.html` (referência H2), servidas por `painel.py` em `/kurokami/ofertas` e `/kurokami/biblioteca` com os dados dentro (`/*DADOS*/{}` trocado por um JSON compacto, gzip) e abertas num `iframe` que ocupa a tela abaixo do topo do painel (`.framesec`, `--topoH`). Filtram, ordenam e desenham tudo no navegador, como as amostras (código delas quase intacto: CSS e JS isolados do painel). Para a ficha do jogo (a B+ do painel, com a caixa do veredito e ‹ › pelos jogos da lista), o carrinho e a loja, chamam `parent.KH` (mesma origem). O menu do topo escolhe a página de dentro (`FR[aba].sub` → `irSub`); o `/` e o Esc apertados com o foco no painel chamam `window.buscar(tecla)` da página (Esc abre e fecha); nas abas sem página própria, o Esc marca `FR.vale.busca` e vai para Ofertas, que abre a busca ao carregar (`buscaPend`). Na Biblioteca, `S.busca` mostra a barra `.bq` no alto da `.tool` e filtra a página como antes. Em Ofertas a busca é um modo próprio (`S.busca`, `pagBusca`): procura o nome (sem acento nem pontuação, todas as palavras) na lista de desejos e nas promoções, ignorando sub-aba, recortes e filtros; Esc abre e fecha (sem ficha nem filtros abertos); trocar de sub-aba também fecha. Dados: `ofertas.py` (`dados_ofertas`: as linhas de `/api/promocoes` da Steam inteira e da lista no formato da amostra, a previsão de `previsao.py` e o histórico de 25 meses por jogo; ~4 s e ~3 MB com 7 mil promoções; `dados_biblioteca`: jogos, franquias e o Completar de `/api/biblioteca`, ~0,5 s). Cache em memória (10 min); `painel.invalidar_linhas` o invalida e o `servico` o remonta em segundo plano depois de cada coleta (`ofertas.aquecer`). Depois de uma verificação, o painel recarrega a página na próxima vez que você entra na aba.

**Previsão** (`previsao.py`, spec 09): piso = menor preço dos últimos 24 meses antes desta promoção (nas lojas marcadas); "se não comprar agora" = a taxa do grupo (tipo de recorde × vezes nesse preço em 24 meses) de `TABELA`, o resultado do backtest (`tools/backtest_previsao.py`) no histórico do dono; a próxima promoção pelo intervalo mediano e pelos grandes eventos do ano anterior (dias em que 200+ jogos da lista começaram promoção), com o preço pela concordância das 6 últimas ou o patamar novo. O veredito (Imperdível, Menor preço, Pode esperar, Preço de costume, Vem aí...) é calculado na página (`verd`).

## Conta Steam (opcional)

**Entrar pela Steam** (`steam_openid.py`, OpenID 2.0, opcional): só o SteamID, gravado em `perfil_steam`. **Finalizar pedido** (aba Carrinho, separada por loja): os itens de outras lojas abrem cada um numa aba (link da ITAD; se o navegador bloquear, ficam como links embaixo do botão); para os da Steam, `POST /api/steam/carrinho` devolve o endereço `store.steampowered.com/cart/#kurokami=…` com os pacotes/bundles e modos; o painel o abre numa aba e a extensão do Hunter (`extensao/`: `carrinho.js` na página do carrinho, `fundo.js` faz as chamadas a `IAccountCartService`, `painel.js` só marca `data-kurokami-ext` no painel) põe os itens com a sessão da própria página, confere e recarrega. Sem a extensão, o painel (só no próprio PC) mostra ao abrir uma faixa "Instalar a extensão do carrinho?" (Instalar / Agora não, pela sessão / Não perguntar mais, `localStorage kr:ext_nao`); Instalar abre a página de extensões do navegador padrão e a pasta, copia o caminho e explica: ligar o Modo do desenvolvedor e arrastar a pasta. "Pronto" recarrega e confere a marca. Programa nenhum consegue instalar extensão sozinho: o Chrome desligou o `--load-extension` em 2025 e registro/políticas só aceitam extensões da Chrome Web Store. Ver `docs/decisoes.md`, "Login Steam".

## Distribuição

- **Pelo código**: `KurokamiRadar_Setup_vX.bat` (payload base64 de um zip) instala em `C:\Kurokami Radar`.
- **Instalado**: GitHub Actions → PyInstaller (onedir, windowed) → Inno Setup → `KurokamiRadar_Setup_vX.exe` em Releases. Programa em `%LOCALAPPDATA%\Programs\Kurokami Hunter` (quem instalou antes da 0.17 continua em `...\Kurokami Radar`: o Inno Setup reaproveita a pasta), dados em `%LOCALAPPDATA%\Kurokami Radar` (`caminhos.py` decide pelo `sys.frozen`).
- **Atualização**: `atualizador.py` consulta `api.github.com/repos/<atualizacao.repo>/releases/latest` ao abrir e a cada 24 h; baixa o `.exe` do release e roda `/VERYSILENT`; o instalador reabre o app (`Check: WizardSilent`).
