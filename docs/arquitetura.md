# Arquitetura

Kurokami Radar é um app **local** de Windows (Python 3.12) que monitora a lista de desejos da Steam em várias lojas, guarda o histórico de preços em SQLite, notifica pela central do Windows e serve um painel web em `http://localhost/kurokami`. Não existe servidor do projeto: cada usuário roda tudo no próprio PC, com as próprias chaves de API.

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
- **Notificações**: `notificar.py` monta XML de toast e chama PowerShell (`-EncodedCommand`, janela oculta). O app se registra em `HKCU\Software\Classes\AppUserModelId\Kurokami.Radar` para aparecer com nome e ícone.

## Fontes de dados e o papel de cada uma

| Fonte | Usada para | Limites conhecidos |
|---|---|---|
| Steam `IStoreBrowseService/GetItems` (sem chave) | catálogo da lista, preços Steam, análises, edições/pacotes, bundles, capas, franquia, fim do desconto | lotes de 50; sem limite publicado |
| Steam `GetWishlist` (sem chave) | lista de desejos e prioridade | perfil precisa ter "Detalhes dos jogos" público |
| Loja Steam (`appdetails`, `packagedetails`) | lista de DLCs de cada jogo; conteúdo das edições | ~200 chamadas / 5 min (ritmo 1,6 s); `GetDLCForApps` exige chave de parceiro, por isso este plano B |
| Steam Web API (chave opcional) | `ResolveVanityURL` (plano B), `GetOwnedGames` | — |
| `userdata.json` (opcional, manual) | DLCs que o usuário possui, carrinho da Steam | é um retrato; envelhece |
| IsThereAnyDeal (chave obrigatória) | preços em ~34 lojas BR (com DRM), histórico (`history/v2`), menor histórico, expiração da oferta | limita ritmo; 200 ids por chamada de preços |
| GG.deals (chave opcional) | melhor preço oficial e keyshop + mínimos | atualiza 1x/h; não diz a loja; erra em jogos com "edição parcial" |

## Ciclo de coleta (`coleta.atualizar`)

1. Perfil → SteamID (XML público do perfil; API como reserva). Lista de desejos (+ `extras` do config). Biblioteca = `userdata.json` ∪ `GetOwnedGames` ∪ `tenho_manual`.
2. **Catálogo Steam** (a cada `intervalos_minutos.steam`, ou forçado): detalhes da lista, conteúdo das edições, listas de DLC (plano B pela loja, com orçamento `chamadas_lentas_por_rodada`), bundles e itens de bundles. Se sobrar fila lenta, o catálogo roda de novo no próximo ciclo.
3. **Biblioteca** (1x/dia): detalhes de tudo que o usuário tem + menor histórico na ITAD das DLCs que faltam.
4. **ITAD**: mapeia appid→id ITAD; importa histórico uma vez por jogo (todas as lojas); preços atuais de todas as lojas → `preco` (só quando muda) e `oferta_atual` (snapshot vigente).
5. **GG.deals** (a cada 60 min).
6. **Custo completo** dos jogos em modo "completo" vira uma "loja" própria no histórico (`Completo (Steam)`).

Verificação **rápida** = o ciclo normal (respeita intervalos e orçamento). **Completa** = `forcar=True, sem_limite=True`; a primeira é sempre completa, depois a cada `verificacao_completa_dias`.

## Avaliação (`analise.avaliar`)

Por jogo da lista (exceto os que o usuário já tem): para cada oferta das **lojas marcadas** (e DRM Steam, se exigido) roda `analise.analisar(linhas, preco, corte)`:
- `linha_do_tempo` junta o histórico das lojas marcadas em trechos (menor preço, corte do menor, maior corte); `episodios` vira promoções (intervalo sem desconto < 1 dia não separa).
- **Raridade** (eixo 1): episódios anteriores com corte ≥ atual − 5, por ano, nos últimos 24 meses. Comum ≥ 3/ano · Incomum 1,5–3 · Raro 0,75–1,5 · Ultrarraro < 0,75 · Lendário = nunca (histórico inteiro), com ≥ 24 meses de histórico e ≥ 1 promoção anterior; 12–24 meses: no máximo Ultrarraro. Sem promoção anterior nas lojas marcadas ou histórico < 6 meses: no máximo Incomum.
- **No piso** (eixo 2): corte ≥ maior corte da vida − 5, ou preço ≤ menor de 24 meses + 1%. **Selo Kurokami** = no piso + Raro ou melhor + ≥ 12 meses + corte ≥ `selo_corte_minimo`.
- **Pílula de piso** (reais, só informativa): compara com o menor preço *antes* do episódio de preço atual: novo / raro (≥ 18 meses sem esse nível ou ≤ 50% do recorde) / igual / 24m.
- **Score** (só ordenação): corte × peso da raridade (0,4…1,0) + 10 no piso. Análises não entram em nada.

Alerta se tem Selo, ou raridade ≥ `raridade_minima` e corte ≥ `desconto_minimo` (favoritos, posições 1..`favoritos_top` da wishlist: a partir de Incomum e sem desconto mínimo). Modo completo e keyshop têm regras próprias. Saída agrupada: um alerta por jogo, Selo primeiro.

## Notificação (`notificador.Notificador`)

Linha de base na primeira vez (não dispara nada em massa) → avisa novidades, quedas ≥ `melhora_minima_reais` e jogos que "rearmaram" (saíram e voltaram). Respeita pausa, horário de silêncio (guarda pendentes), máximo por rodada (resto vira resumo) e silenciados. Avisos de "termina em breve" para carrinho/vale a pena.

## Painel

`painel.html` é um SPA único (HTML+CSS+JS inline, sem build), visual da loja Steam. Lê tudo via `/api/*` (ver `api.md`). Localhost sempre liberado; outros aparelhos só com PIN (cookie `kr`) e se `painel.rede_local` estiver ligado. Porta 80 com reserva na 8787.

## Ponte com a Steam (`ponte.user.js`)

Userscript do Tampermonkey que roda em `store.steampowered.com`, lê `/api/ponte` do Radar local e, usando a sessão do usuário **dentro do navegador**, adiciona itens ao carrinho (`/cart/addtocart`, com plano B de clicar no botão da página e passar a verificação de idade) e aplica a fila da lista de desejos (`/api/addtowishlist`, `/api/removefromwishlist`). O Radar nunca recebe cookies da Steam.

## Distribuição

- **Pelo código**: `KurokamiRadar_Setup_vX.bat` (payload base64 de um zip) instala em `C:\Kurokami Radar`.
- **Instalado**: GitHub Actions → PyInstaller (onedir, windowed) → Inno Setup → `KurokamiRadar_Setup_vX.exe` em Releases. Programa em `%LOCALAPPDATA%\Programs\Kurokami Radar`, dados em `%LOCALAPPDATA%\Kurokami Radar` (`caminhos.py` decide pelo `sys.frozen`).
- **Atualização**: `atualizador.py` consulta `api.github.com/repos/<atualizacao.repo>/releases/latest` ao abrir e a cada 24 h; baixa o `.exe` do release e roda `/VERYSILENT`; o instalador reabre o app (`Check: WizardSilent`).
