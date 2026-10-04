# Referência de módulos e funções

Gerado a partir do código (assinatura + primeira parte da docstring). Para regenerar: `py tools/gerar_referencia.py`.

## `radar.py`
KUROKAMI RADAR - linha de comando (o app instalado usa os mesmos comandos: KurokamiRadar.exe <comando>)

- `brl(c)`
- `pedir_chaves_se_faltar()`
- `achar_jogo(banco, termo)`
- `cmd_testar(cfg, _)`
- `cmd_lojas(cfg, _)`
- `cmd_sondar(cfg, args)` — Respostas cruas, sem chaves e sem dados pessoais, para conferir os formatos.
- `cmd_atualizar(cfg, args)`
- `cmd_verificar(cfg, args)`
- `cmd_historico(cfg, args)`
- `cmd_caminhos(cfg, args)`
- `cmd_dlcs(cfg, args)`
- `menu()`
- `cmd_conteudo(cfg, args)` — py radar.py conteudo hitman "Deluxe Edition" "Deluxe Pack|Seven Deadly"
- `cmd_ciclo(cfg, args)`
- `cmd_testar_notificacao(cfg, args)`
- `cmd_inicio(cfg, args)`
- `cmd_classificar(cfg, args)` — py radar.py classificar hitman "Trinity|Street Art|Makeshift" cosmetico
- `main()`

## `radar/__init__.py`
Kurokami Radar - monitor de promocoes da wishlist Steam.


## `radar/analise.py`
Score, custo completo, bundles com desconto do que voce ja tem e regras de alerta.

- `etiqueta(preco, cheio, pisos, cfg_alerta, flag)` — Qual o 'tamanho' do piso que este preco atinge. Devolve (tag, texto, acima_do_menor_de_sempre).
- `_ts(q)`
- `_iso(t)`
- `_igual(preco, ref)` — Centavos de diferenca (<= R$ 0,10 ou 1%) contam como igual.
- `linha_do_tempo(linhas, agora_)` — Junta o historico das lojas marcadas numa linha so: [(ini, fim, menor_preco, corte_do_menor, maior_corte)].
- `episodios(segs, folga)` — Promocoes como episodios: [(ini, fim, maior_corte)]. Um intervalo sem desconto menor que `folga`
- `analisar(linhas, preco, corte, agora_, cfg_alerta)` — Raridade v2 (frequencia do corte), piso (eixo 2), pilula de piso (reais) e Selo Kurokami.
- `tipos_de(an)` — Tipos de preco da oferta (nao exclusivos): selo, novo (inclui "raro" sem Selo), igual, 24m.
- `tipos_ligados(cfg_alerta)` — Tipos que avisam, pelo config (alerta.tipos). Sem a chave (config antigo): so o Selo.
- `avisa_por(tipos, corte, cfg_alerta)` — Tipos ligados que fazem a oferta avisar: o Selo sempre (o selo_corte_minimo ja esta nele); os outros so com
- `tipo_oferta(tipos)` — O tipo exclusivo (o mais importante) ou None.
- `costuma_voltar(an, corte)` — Coluna "Costuma voltar" (so informa; spec 04): (texto, ordem). ordem menor = mais raro; None = fim da lista
- `dica_volta(an, corte)` — A linha da dica (e da ficha): "Nos últimos 2 anos: N vezes com -Y% ou mais (última em mm/aaaa) · maior
- `motivo_tipo(an, tipo)` — O motivo do aviso pelo tipo (A.7 da spec 04). piso_ref e o menor antes do episodio atual (de sempre,
- `menor_anterior(linhas, ref)` — O registro que fez o menor preco anterior (piso_ref): (loja, preco, quando) do ultimo registro com esse preco
- `regua_steam(linhas, preco, corte, linhas_steam, preco_s, corte_s, agora_, cfg_alerta)` — Regua so da Steam ("Steam (direto)" + Steam da ITAD) x lojas marcadas. Informativo, nunca avisa.
- `_score_v2(corte, nivel, no_piso)` — 0-100 sem analises: corte x peso da raridade, +10 no piso.
- `favorito(jogo, cfg_alerta)` — Esta entre os N primeiros da ordem que voce deu na lista de desejos?
- `texto_outras(a)` — Outras lojas que tambem bateram o alerta com ate R$ 1 a mais:
- `raridade_ok(nivel, minimo)`
- `_brl(c)`
- `tag_minima_ok(tag, cfg_alerta)` — A etiqueta atinge o minimo que o usuario pediu para 'valer a pena'?
- **class `Contexto`** — Carrega uma vez o que a analise precisa do banco.
  - `preco(appid)`
  - `relevantes(appid)` — Base + DLCs que importam (sem cosmeticos etc., conforme o config).
  - `caminhos(appid)` — Todas as formas de ter o jogo, com cobertura do conteudo relevante e custo para completar.
  - `precos_parciais(appid)`
  - `preco_bundle_pra_voce(o)` — Regra da Steam: voce paga so pelos itens que nao tem, com o desconto do bundle.
  - `melhor_completo(appid)`
  - `melhor_combinacao(appid, max_opcoes)` — Jeito mais barato de ter base + DLCs relevantes, combinando bundles/edicoes e itens avulsos.
  - `_opcoes_das_dlcs(appid)` — Bundles/edicoes ligados as DLCs do jogo (alem dos ligados ao proprio jogo).
- `avaliar(ctx, ofertas_itad, gg, lojas_marcadas)` — Devolve a lista de alertas que dispararia agora. ofertas_itad: {appid: [oferta]}.
- `ordem_tipo(t)`
- `chave_aviso(a)` — Ordem dos avisos (e do max_por_rodada): selo, novo, igual, 24m (keyshop e completo depois); maior corte primeiro.

## `radar/atualizador.py`
Atualizacao pelo GitHub Releases: verifica, baixa o instalador novo e instala por cima (dados ficam).

- `_v(t)`
- `repo()`
- `verificar()` — {"atual","nova","tem_nova","url_exe","pagina","notas"} ou {"erro": ...}
- `baixar(url, progresso)`
- `instalar(instalador)` — Roda o instalador em silencio, separado deste processo; ele fecha o Radar, instala e abre a versao nova.
- `abrir_janela_separada()` — Abre a janela de atualizacao num processo proprio (a bandeja ocupa a thread principal).
- `janela()` — Kurokami Radar (Atualizar): mostra as versoes e atualiza com um clique.

## `radar/banco.py`
SQLite local. Precos sao gravados so quando mudam, entao o historico

- `agora()`
- `utc(ts)` — Tudo em UTC no mesmo formato, para a ordenacao por texto funcionar.
- **class `Banco`** — 
  - `_migrar()`
  - `commit()`
  - `q(sql)`
  - `um(sql)`
  - `meta(chave, valor)`
  - `salvar_jogo(j)`
  - `marcar_listas(wishlist, possuidos, prioridade)`
  - `definir_itad(appid, gid)`
  - `salvar_dlc(appid, pai, classe)`
  - `salvar_opcao(o)`
  - `itens_opcao(oid)`
  - `consultado(tipo, ident, dias)`
  - `marcar_consulta(tipo, ident)`
  - `ultima_consulta(tipo, ident)`
  - `limpar_consulta(tipo, ident)`
  - `ligar_opcao(appid, oid)`
  - `registrar_preco(appid, loja, preco, cheio, corte, fonte, url, quando)` — Grava so se mudou desde o ultimo registro dessa loja.
  - `importar_historico(appid, registros)` — registros: [(loja, preco, cheio, corte, quando)] vindos da ITAD.
  - `menor(appid, lojas, dias)` — Menor preco registrado. dias: so olha essa janela (0/None = desde sempre).
  - `linhas_lote(lojas, appids)` — {appid: [registros de preco em ordem]} das lojas dadas, para a lista inteira (ou os appids dados).
  - `pisos_lote(lojas, janelas)` — Igual a pisos(), para todos os jogos da lista de uma vez.
  - `_pisos_de(rows, janelas)`
  - `pisos(appid, lojas, janelas)` — {dias: menor preco na janela, 0: menor de todos os tempos} considerando so as lojas dadas.
  - `atuais(appid)` — Ultimo preco de cada loja.
  - `salvar_ofertas_atuais(ofertas)` — O que as lojas vendem AGORA (ultima resposta da ITAD). O historico nao serve para isso:
  - `ofertas_atuais(appids)` — {appid: [oferta]} vigentes, com a Steam lida direto do catalogo quando a ITAD nao traz a Steam.
  - `salvar_gg(appid, g)`

## `radar/bandeja.py`
Icone na bandeja do Windows. Roda o servico em segundo plano.

- `desenhar_icone(cor_ponto)`
- `abrir(caminho)`
- `abrir_log()` — Abre o log; se ainda nao existe (nada foi registrado), cria vazio antes.
- `_comando_atual()`
- `main(esperar, abrir_painel)`

## `radar/caminhos.py`
Pastas do app.

- `_migrar()` — Instalado pela primeira vez: traz banco, config e userdata da versao que rodava pelo codigo.
- `garantir()`
- `achar_userdata(cfg)` — Procura o userdata.json: na pasta de dados, ao lado do programa, no caminho do config

## `radar/coleta.py`
Orquestra a coleta: Steam (catalogo) -> ITAD (precos por loja + historico) -> GG.deals.

- `_min_desde(banco, chave)`
- `atualizar(cfg, banco, forcar, importar_hist, sem_limite, log)`
- `catalogo_steam(cfg, banco, wl, possuidos, sid, k_steam, log, orcamento)`
- `coletar_biblioteca(cfg, banco, possuidos, k_itad, log)` — Precos, franquias e menor historico de tudo que voce tem (jogos e DLCs).
- `_cache_itad(cfg, banco)`
- `coletar_itad(cfg, banco, wl, chave, importar_hist, log)`

## `radar/config.py`
config.json: tudo que nao e segredo. O painel web (etapa 3) vai editar este arquivo.

- `_mesclar(base, novo)`
- `carregar()`
- `salvar(cfg)`
- `modo_do_jogo(cfg, appid)`

## `radar/conta_steam.py`
Relacao da sua conta Steam com os jogos: seguidos e ignorados (spec 04, B).

- `_vazio()`
- `relacao(cfg)` — {"seguidos": set[int], "ignorados": set[int], "fonte": "userdata" | None, "quando": iso | None}.
- `assinatura(cfg)` — (arquivo, data de modificacao) do userdata.json: muda quando o arquivo muda (o cache do painel usa).

## `radar/credenciais.py`
Chaves de API no Gerenciador de Credenciais do Windows (via keyring).

- `disponivel()`
- `ler(nome)`
- `gravar(nome, valor)`
- `mascarar(v)`
- `limpar(v)` — Chaves sao ASCII visivel: tira espacos, aspas e qualquer caractere de controle
- `configurar_interativo(so_faltando)` — Pergunta as chaves no terminal e testa cada uma na hora. Enter mantem a atual.
- `faltando_obrigatorias()`

## `radar/dlc.py`
Classificacao automatica de DLCs pelo nome (pt/en). O painel vai permitir

- `classificar(nome)`
- `ignorada(classe, preco, cfg_dlc)`

## `radar/ggdeals.py`
GG.deals: melhor preco oficial e de keyshop + menores historicos de cada um.

- **class `ChaveRecusada`** — 
- `precos(chave, appids, regiao, log)`

## `radar/inicio.py`
Iniciar com o Windows: tarefa agendada no logon; se o Windows recusar (sem admin),

- `comando()` — (executavel, argumentos) que abre a bandeja sem janela de console.
- `_atalho()`
- `instalar()`
- `remover()`

## `radar/itad.py`
IsThereAnyDeal: lojas, mapeamento de ids, precos por loja (com DRM) e historico.

- **class `ChaveRecusada`** — 
- `_get(caminho, chave, tentativas)`
- `_post(caminho, chave, corpo)`
- `norm(nome)`
- `lojas(chave, pais)` — [{id, title}] das lojas que a ITAD acompanha no pais.
- `resolver_lojas(chave, pais, nomes)`
- `mapear(chave, appids, cache, log)`
- `_drm_steam(deal)` — A oferta da propria Steam vem com drm vazio; nas outras lojas, vazio = DRM desconhecido.
- `precos(chave, pais, gids, shop_ids, log)` — {gid: {"ofertas": [...], "hist_all": centavos, "hist_y1": ..}} com TODAS as lojas pedidas,
- `historico(chave, pais, gid, shop_ids, dias)` — [(loja, preco, cheio, corte, quando)] do log de precos da ITAD.

## `radar/janela_chaves.py`
Janela de primeiro uso para as chaves. Campo de texto do Windows: Ctrl+V e o botao direito funcionam.

- `abrir()`

## `radar/notificador.py`
Decide QUAIS alertas viram notificacao:

- `brl(c)`
- `em_silencio(cfg, agora_local)`
- **class `Notificador`** — 
  - `_lista_url()`
  - `_vitrine_url()`
  - `processar(alertas)`
  - `_enviar(a)`
  - `_acao(acao, appid)`
  - `terminando(candidatos)` — candidatos: [{"appid","nome","preco","corte","loja","fim"(epoch)}]. Avisa 1x por promocao.

## `radar/notificar.py`
Notificacoes nativas do Windows (central de notificacoes), sem dependencias.

- `registrar_app(icone)`
- `capa(appid, url)` — Baixa a capa do jogo uma vez (vira a imagem grande da notificacao).
- `_uri(caminho)`
- `mostrar(titulo, texto, clique, botoes, imagem, rodape, silenciosa)` — botoes: [(rotulo, url)]. url pode ser http(s) ou file:///.

## `radar/painel.py`
Painel local: servidor HTTP so em 127.0.0.1, com API JSON lendo o banco e a pagina painel.html.

- `token(novo)`
- `ips_locais()`
- `_base(host)`
- `rede_local()`
- `_fim(oferta, jogo)` — Quando a promocao acaba (epoch), pela ITAD ou pela Steam.
- `_marcadas(cfg)`
- `_ultimos_por_loja(b, appids)`
- `_minimos(b, appids)`
- `_idade_userdata()`
- `api_resumo(_q)`
- `invalidar_linhas()`
- `linhas_promocoes()` — (linhas, cfg, conta) do cache, montando de novo se preciso.
- `_montar_linhas(cfg, conta)`
- `api_lista(_q)`
- **class `PedidoInvalido`** — Vira HTTP 400 com a mensagem (em portugues).
- `_ler_q(qs)` — Valida o q= de /api/promocoes. Campo ou valor desconhecido -> PedidoInvalido; ausente = sem filtro.
- `_filtros(f)` — {grupo: predicado}; as contagens de um grupo usam todos os outros.
- `_ordenar(itens, ordem)`
- `api_promocoes(qs)` — Explorador da aba Promocoes: filtra, conta e pagina no Radar (pensando na Steam inteira, spec 07).
- `api_vitrine(_q)` — Prateleiras da aba "Vale a pena": um bloco por tipo (exclusivo), sem os jogos que voce tem. O Selo vale com
- `_rar_info(an)` — O 'por que essa raridade' da ficha.
- `_estado_dlcs(b, a, j)` — Por que a ficha nao tem DLCs: falhou, a Steam nao informou ou ainda nao consultada (com a fila, se rodando).
- `api_jogo(q)`
- `_ler_carrinho()`
- `_gravar_carrinho(itens)`
- `api_carrinho(_q)` — Carrinho simulado: jogos/DLCs (com a loja escolhida) e bundles da Steam (com o preco para voce).
- `post_carrinho(d)` — O carrinho fica num arquivo proprio: gravar nele nunca espera a coleta liberar o banco.
- `api_buscar(q)` — Nome, appid ou link da Steam -> resultados da loja.
- `post_extra(d)` — Passa a monitorar um jogo fora da lista de desejos (ou para de monitorar).
- `api_biblioteca(_q)` — Visao de colecionador: valor da biblioteca, o que falta para completar cada jogo e as franquias.
- `api_acesso(_q)`
- `post_acesso(d)`
- `post_tenho(d)` — Marca/desmarca "ja tenho" (para compras feitas depois do userdata.json).
- `post_silenciar(d)`
- `post_atualizar_tudo(_d)`
- `api_ponte(_q)` — Para a ponte (Tampermonkey) nas paginas da Steam: o que mandar para o carrinho e a fila da lista de desejos.
- `post_ponte_feito(d)`
- `post_lista_steam(d)` — Enfileira adicionar/tirar da lista de desejos da Steam (a ponte executa na proxima pagina da Steam).
- `post_atualizar_app(_d)`
- `post_sair(_d)`
- `api_notificacoes(_q)`
- `api_alertas(_q)`
- `api_config(_q)`
- `post_config(dados)`
- `post_dlc(d)`
- `post_modo(d)`
- `post_verificar(_d)`
- `post_pausar(_d)`
- `_log_erro(rota, e)`
- **class `Handler`** — 
  - `log_message()`
  - `_local()`
  - `_autorizado(u)` — Do proprio PC: sempre. De outro aparelho: so depois de digitar o PIN (fica lembrado por 1 ano).
  - `_pagina_pin(erro)`
  - `_entrar()`
  - `_json(obj, code)`
  - `do_GET()`
  - `do_POST()`
- `iniciar(abrir)`
- `reiniciar()` — Troca entre so-este-PC e rede local sem fechar o Radar.
- `url()`

## `radar/progresso.py`
Em que parte da checagem o Radar esta (para o painel e o icone da bandeja).

- `iniciar(modo)`
- `etapa(nome, total)`
- `passo(atual, total)`
- `linha(msg)` — Cada linha do log tambem vira progresso: linha sem recuo = etapa nova.
- `fim(ok, resumo)`
- `foto()`

## `radar/rede.py`
HTTP com JSON, backoff em 429/5xx e ritmo adaptativo (mesma logica do KurokamiPrecos).

- **class `Ritmo`** — 
  - `aguardar()`
  - `freio(pausa)`
  - `ok()`
- `http_json(url, corpo, metodo, ritmo, tentativas, timeout, form)`
- `servico_steam(url, entrada, chave, ritmo)` — Endpoints 'Service' da Steam: GET com input_json; POST so se o GET der 405.
- `explicar(e)` — Mensagem curta de um erro HTTP, com o motivo que o servidor mandou.
- `lotes(seq, n)`
- `centavos(v)` — Centavos como a Steam manda ("413" ou 413).
- `de_reais(v)` — Valor decimal (ITAD amount, GG.deals "9.99" ou "10") para centavos.

## `radar/relatorio.py`
Pagina local com os alertas atuais (ponte ate o painel da etapa 3). Abre no navegador.

- `gerar(alertas, capas, novos_ids)`

## `radar/series.py`
Agrupa jogos da mesma serie pelo nome, em vez do campo "franquia" da Steam

- `tokens(nome)`
- `chave(nome)`
- `rotulo(nomes)` — Prefixo comum dos nomes, recortado do primeiro nome original (mantem a grafia: "Half-Life", "Need for Speed").
- `agrupar(itens)` — itens: [{"appid", "nome", ...}] -> {chave: [itens]}

## `radar/servico.py`
O ciclo que roda sozinho: coleta -> avalia -> notifica, no intervalo do config.

- `criar_log(eco)`
- `_fim_iso(v)`
- `candidatos_fim(b, alertas, cfg)` — O que esta no carrinho ou "vale a pena" e tem data de fim conhecida (ITAD ou Steam).
- `ciclo(log, forcar, sem_limite)` — Uma rodada. forcar+sem_limite = verificacao completa. Devolve (alertas, novos).
- **class `Servico`** — 
  - `_precisa_completa()` — 1a checagem e sempre completa; depois, a cada N dias (config verificacao_completa_dias).
  - `agora(completo)`
  - `run()`

## `radar/steam.py`
Steam: lista de desejos, biblioteca, detalhes da loja, DLCs e opcoes de compra.

- `resolver_steamid(chave, perfil)` — SteamID64 a partir do perfil. Tenta primeiro sem chave (perfil publico, XML da comunidade).
- `wishlist(chave, steamid)`
- `biblioteca_api(chave, steamid)`
- `ler_userdata(arquivo)`
- `url_asset(item)`
- `_nome_norm(s)`
- `_edicoes(item)` — Pacotes (edicoes) que vendem este app, sem os bundles.
- `_edicao_base(item, eds)` — Qual pacote e 'o jogo'. Nao e o mais barato: o HITMAN WoA vende a 'Part One' a R$ 8,89,
- `_tem_partes(eds)`
- `get_items(ids, pais, extra, chave, por_lote, log)` — ids: [{"appid":x}] / [{"bundleid":x}] / [{"packageid":x}]. Devolve a lista crua de store_items.
- `normalizar_app(it)`
- `_pacotes_uma_chamada(ids, pais)`
- `conteudo_pacotes(packageids, pais, log)` — {packageid: [appids]} via packagedetails da loja - o unico lugar que lista as DLCs de uma edicao.
- `dlcs_pela_loja(appid, pais)` — Plano B quando o GetDLCForApps recusa: appdetails da loja (1 jogo por chamada, limite ~200/5min).
- `dlcs_dos_jogos(chave, steamid, appids, pais, log)` — {appid_dlc: appid_pai} via GetDLCForApps (leitura tolerante, como no KurokamiPrecos).
- `_appids_em(no)`
- `normalizar_opcao(it, tipo)` — Bundle ou pacote (edicao) com a lista de apps que ele inclui.

## `radar/validar.py`
Testa cada chave com uma chamada real e explica o resultado.

- `formato_suspeito(nome, chave)`
- `testar(nome, chave)` — (ok, mensagem)
- `testar_perfil(perfil)` — (ok, mensagem, steamid). Usa so dados publicos: nao precisa de chave.
