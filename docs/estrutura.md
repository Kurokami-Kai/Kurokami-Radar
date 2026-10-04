# Estrutura de arquivos

```
Kurokami Radar/
├── radar.py                 # CLI e ponto de entrada (também do .exe); sem args no .exe = bandeja
├── radar/                   # pacote principal
│   ├── __init__.py          # VERSAO (fonte única da versão)
│   ├── caminhos.py          # pastas: código x dados (instalado usa %LOCALAPPDATA%), migração
│   ├── config.py            # PADRAO do config.json + carregar/salvar (merge com o arquivo)
│   ├── credenciais.py       # chaves no Gerenciador de Credenciais (keyring), entrada pelo terminal
│   ├── validar.py           # testa chaves e perfil com chamadas reais; dicas de erro
│   ├── janela_chaves.py     # janela Tk "Perfil e chaves" (primeira abertura)
│   ├── rede.py              # http_json, servico_steam (GET input_json), Ritmo (rate limit adaptativo)
│   ├── steam.py             # wishlist, GetItems, edições/pacote base, DLCs pela loja, bundles
│   ├── itad.py              # lojas, lookup, preços v3 (1 oferta por loja), histórico
│   ├── ggdeals.py           # preços oficial/keyshop
│   ├── banco.py             # SQLite: esquema, migrações, preços, pisos, ofertas vigentes
│   ├── coleta.py            # orquestra a coleta (catálogo, biblioteca, ITAD, GG, custo completo)
│   ├── dlc.py               # classificação de DLCs por nome
│   ├── series.py            # agrupa jogos da mesma série pelo nome (aba Biblioteca)
│   ├── analise.py           # raridade v2 (episódios), piso, Selo, score, etiquetas, caminhos/combinação de compra, avaliar()
│   ├── notificar.py         # toast do Windows via PowerShell; capa do jogo
│   ├── notificador.py       # regras de envio (linha de base, tipo recém-ligado vira resumo, rearme, silêncio, fim de promoção)
│   ├── conta_steam.py       # seguidos e ignorados da conta Steam (userdata.json); único leitor de rgFollowedApps/rgIgnoredApps
│   ├── servico.py           # ciclo() e thread Servico (agenda, completa periódica)
│   ├── progresso.py         # estado da checagem em andamento (painel e tooltip)
│   ├── relatorio.py         # dados/alertas.html (página estática de reserva)
│   ├── painel.py            # servidor HTTP + API JSON + PIN + rotas da ponte
│   ├── painel.html          # o painel inteiro (HTML/CSS/JS inline)
│   ├── ponte.user.js        # userscript Tampermonkey (servido em /kurokami/ponte.user.js)
│   ├── bandeja.py           # ícone, menu, threads, verificação de versão
│   ├── inicio.py            # iniciar com o Windows (versão pelo código)
│   └── atualizador.py       # GitHub Releases: verificar, baixar, instalar silencioso; janela Tk
├── tools/
│   ├── gerar_icone.py       # assets/radar.ico para o .exe/instalador
│   ├── gerar_referencia.py  # regenera docs/referencia.md
│   ├── mapa.py              # mapa de seções/funções com linhas (ler só o trecho)
│   ├── exportar_docs.py/.bat # reserva: docs → Área de Trabalho\kurokami-docs (o Projeto do claude.ai já lê do GitHub)
│   ├── backtest_selo.py     # backtest do Selo e variantes sobre uma cópia temporária do banco (só números agregados)
│   ├── backtest_tipos.py    # spec 04: backtest por tipo de recorde (Selo, novo, igual, 24m), métrica "não ficou mais barato em 12 meses"
│   ├── medir_spec04.py      # spec 04: vitrine, avisos de hoje (regra atual × só Selo), userdata, DLCs em promoção, tempo do /api/lista
│   ├── teste_promocoes_steam.py  # spec 04: viabilidade de "Steam inteira" (ITAD deals, IStoreQueryService, busca da loja); só lê; --retrato grava os preços
│   ├── regua_steam.py       # spec 04 (1c): o Radar × "só a Steam" nos recordes raros, storeLow da ITAD e custo do histórico da Steam inteira
│   ├── testar_piso.py       # testes sintéticos do piso, Lendário, Selo (só G), tipos e "Costuma voltar", sem rede nem banco
│   ├── testar_avisos.py     # regra de aviso da 0.15 numa cópia do banco (só Selo, ligar/desligar tipos, resumo ao ligar)
│   ├── testar_promocoes.py  # /api/promocoes e /api/vitrine numa cópia do banco (tempos, filtros, ordenação, 400)
│   ├── painel_copia.py      # sobe o painel numa cópia do banco (porta 8799), sem coleta: para ver o visual e tirar prints
│   └── checar.py            # checagens antes de entregar (sintaxe, JS, versão, add-data, dados pessoais, .gitignore, testar_piso)
├── docs/                    # esta documentação
├── .github/workflows/gerar-instalador.yml   # build do Setup.exe em Releases
├── installer.iss            # Inno Setup (instalação por usuário, sem admin)
├── gerar_setup.bat          # build local do Setup.exe (precisa do Inno Setup)
├── instalar.bat             # instalação pelo código (pip + chaves + bandeja)
├── requirements.txt         # keyring, pystray, Pillow
├── README.md                # guia do usuário (página do GitHub)
├── TECNICO.md               # notas técnicas para quem roda pelo código
├── CLAUDE.md                # instruções para o Claude Code
└── .claude/skills/          # skills do Claude Code (comece por kurokami-code)
```

## Arquivos de dados (nunca vão para o git)

Pelo código ficam ao lado do `radar.py`; instalado, em `%LOCALAPPDATA%\Kurokami Radar`:

```
config.json            preferências (sem segredos)
userdata.json          retrato da conta Steam (DLCs possuídas, carrinho) — pessoal
dados/radar.sqlite3    banco (WAL)
dados/radar.log        log rotativo (1 MB × 3)
dados/carrinho.json    carrinho simulado (arquivo próprio para não disputar lock com a coleta)
dados/painel_token.txt PIN de 6 dígitos do acesso pela rede
dados/capas/<appid>.jpg imagens das notificações
dados/alertas.html     página de reserva
dados/sonda/sonda.json respostas cruas das APIs (comando sondar)
```
