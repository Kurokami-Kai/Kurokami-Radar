# Referência de módulos e funções

Gerado a partir do código (assinatura + primeira parte da docstring). Para regenerar: `py tools/gerar_referencia.py`.

## `radar.py`
KUROKAMI HUNTER - linha de comando (o app instalado usa os mesmos comandos: KurokamiRadar.exe <comando>)

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
Kurokami Hunter - monitor de promocoes da wishlist Steam.


## `radar/analise.py`
Score, custo completo, bundles com desconto do que voce ja tem e regras de alerta.

- `etiqueta(preco, cheio, pisos, cfg_alerta, flag)` — Qual o 'tamanho' do piso que este preco atinge. Devolve (tag, texto, acima_do_menor_de_sempre).
- `_ts(q)`
- `_iso(t)`
- `_igual(preco, ref)` — Centavos de diferenca (<= R$ 0,10 ou 1%) contam como igual.
- `_metade(preco, recorde)` — Preco pela metade do recorde anterior, com a mesma folga de centavos do "igual" (R$ 0,10 ou 1% da metade).
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
- `_brl(c)`
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
- `instalar(instalador)` — Roda o instalador em silencio, separado deste processo; ele fecha o Hunter, instala e abre a versao nova.
- `abrir_janela_separada()` — Abre a janela de atualizacao num processo proprio (a bandeja ocupa a thread principal).
- `janela()` — Kurokami Hunter (Atualizar): mostra as versoes e atualiza com um clique.

## `radar/banco.py`
SQLite local. Precos sao gravados so quando mudam, entao o historico

- `agora()`
- `utc(ts)` — Tudo em UTC no mesmo formato, para a ordenacao por texto funcionar.
- **class `Banco`** — 
  - `_migrar()`
  - `_migrar_2()`
  - `commit()`
  - `q(sql)`
  - `um(sql)`
  - `meta(chave, valor)`
  - `salvar_jogo(j)`
  - `marcar_listas(wishlist, possuidos, prioridade)`
  - `salvar_tempo_jogo(tempos)` — tempos: {appid: (minutos, ultima_unix)} da ultima leitura da biblioteca; substitui tudo.
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

- `desenhar_icone(cor_ponto, tam)` — Mira preta e vermelha do Kurokami Hunter (o mesmo desenho do logo do painel). Desenha em 4x e reduz (bordas lisas).
- `abrir(caminho)`
- `abrir_log()` — Abre o log; se ainda nao existe (nada foi registrado), cria vazio antes.
- `_comando_atual()`
- `main(esperar, abrir_painel)`

## `radar/cambio.py`
Câmbio para o histórico da ITAD.

- `moeda_do_pais(pais)`
- `_arquivo()`
- `_ler()`
- `_baixar()` — Reais por unidade de cada moeda (a API dá moedas por real; inverte). None se a rede falhar.
- `taxas()` — {moeda: reais por unidade}. Cache em memória e em disco por 24 h; nunca levanta erro.
- `em_reais(valor, moeda, alvo)` — Valor decimal na `moeda` para a moeda do país (alvo). Igual ao alvo ou sem moeda: devolve como veio.

## `radar/caminhos.py`
Pastas do app.

- `_migrar()` — Instalado pela primeira vez: traz banco, config e userdata da versao que rodava pelo codigo.
- `garantir()`
- `achar_userdata(cfg)` — Procura o userdata.json: na pasta de dados, ao lado do programa, no caminho do config

## `radar/coleta.py`
Orquestra a coleta: Steam (catalogo) -> ITAD (precos por loja + historico) -> GG.deals.

- `_min_desde(banco, chave)`
- `atualizar(cfg, banco, forcar, importar_hist, sem_limite, log, steam_agora)`
- `catalogo_steam(cfg, banco, wl, possuidos, sid, k_steam, log, orcamento)`
- `coletar_biblioteca(cfg, banco, possuidos, k_itad, log)` — Precos, franquias e menor historico de tudo que voce tem (jogos e DLCs).
- `_cache_itad(cfg, banco)`
- `coletar_itad(cfg, banco, wl, chave, importar_hist, log)`

## `radar/config.py`
config.json: tudo que nao e segredo. O painel web (etapa 3) vai editar este arquivo.

- `_mesclar(base, novo)`
- `carregar()`
- `_migrar(cfg)`
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

## `radar/ficha.py`
Ficha do jogo (spec 09): o que so a ficha usa. Buscado ao abrir (nunca na coleta) e guardado em ficha_cache:

- `_do_cache(b, a, fonte)`
- `_num(v)`
- `_url(v)` — Servico de terceiro sem contrato: so link https vai para a pagina.
- `augmented(appid)` — HLTB em minutos (FF VII Remake: 1935 = 32 h, como no site), jogadores e notas de usuarios/criticos.
- `extras(b, cfg, a, tenho, log_erro)` — {loja, aug, conq}: do cache ou buscados em paralelo (o que faltar ou venceu). Fonte que falhou vem None.
- `hltb_lote(b, appids, log_erro, maximo)` — {appid: {story, extras, complete} em minutos, ou None}: o HLTB de varios jogos (ficha da franquia), do mesmo
- `jogado(b, a)`
- `fileira(b, ctx, a, nome, marcadas)` — A franquia do jogo entre os que o Hunter conhece (biblioteca e lista), em ordem de lancamento, com o preco de

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
- `menores(chave, pais, gids, log)` — Steam inteira (spec 07): {gid: {"flag", "hl", "hl1"}} em lotes de 200. flag e a marca da ITAD na oferta da
- `historico(chave, pais, gid, shop_ids, dias, desde, tentativas)` — [(loja, preco, cheio, corte, quando)] do log de precos da ITAD. desde (ISO): so o que veio depois.

## `radar/janela_chaves.py`
Janela de primeiro uso para as chaves. Campo de texto do Windows: Ctrl+V e o botao direito funcionam.

- `abrir()`

## `radar/notificador.py`
Decide QUAIS alertas viram notificacao:

- `brl(c)`
- `em_silencio(cfg, agora_local)`
- **class `Notificador`** — 
  - `_avisar(titulo, texto, clique, botoes, imagem, rodape, foto)` — Um aviso, nos dois canais: toast do Windows (se ativo) e Telegram (se ligado).
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

## `radar/ofertas.py`
Dados das páginas novas de Ofertas e Biblioteca (spec 09, amostra 8 de Ofertas e referência H2 da Biblioteca).

- `invalidar()`
- `_cache(nome, fazer)` — Um cálculo por vez para cada página; quem chega no meio espera o mesmo resultado.
- `curta(u)`
- `_linhas_de(b, tabela, lojas, appids)`
- `_todas(q)` — Todas as páginas de /api/promocoes com o pedido q (no próprio processo).
- `_linha(o, cv, fr, hist, prev, an)` — Uma linha no formato da amostra (os índices são lidos pela função M() da página).
- `_montar_ofertas()`
- `dados_ofertas()`
- `_montar_biblioteca()`
- `dados_biblioteca()`
- `aquecer(atraso)` — Monta as duas em segundo plano (depois de uma coleta ou de um POST), para a página abrir na hora.

## `radar/painel.py`
Painel local: servidor HTTP so em 127.0.0.1, com API JSON lendo o banco e a pagina painel.html.

- `montar_painel()` — painel.html com cada /*incluir arquivo*/ trocado pelo arquivo de painel-web/: o navegador recebe uma página só, como antes.
- `token(novo)`
- `ips_locais()`
- `_base(host)`
- `rede_local()`
- `_fim(oferta, jogo)` — Quando a promocao acaba (epoch), pela ITAD ou pela Steam.
- `_marcadas(cfg)`
- `_melhor_oferta(ofs)` — A oferta mais barata; no empate, a da Steam (o carrinho dela vai sozinho pela extensao).
- `_ultimos_por_loja(b, appids)`
- `_minimos(b, appids)`
- `_idade_userdata()`
- `_perfil_info(b)` — Nome e avatar do perfil Steam em uso (meta perfil_info). Se faltar ou for de outro SteamID, busca numa thread
- `api_resumo(_q)`
- `invalidar_linhas()`
- `linhas_promocoes()` — (linhas, cfg, conta) do cache, montando de novo se preciso.
- `_montar_linhas(cfg, conta)`
- `api_lista(_q)`
- **class `LinhaSteam`** — Linha leve da Steam inteira: o["campo"] como nas linhas da lista; o que ela nao tem vale None (False na relacao).
  - `como_dict()`
- `_aplicar_aval(o, aval)` — steam_promo.aval (JSON) -> campos da avaliacao da LinhaSteam.
- `linhas_steam(itens_lista)` — Linhas leves da Steam inteira (sem quem ja esta na lista) e quando foi a coleta. Refaz quando ha coleta nova.
- **class `PedidoInvalido`** — Vira HTTP 400 com a mensagem (em portugues).
- `_ler_q(qs)` — Valida o q= de /api/promocoes. Campo ou valor desconhecido -> PedidoInvalido; ausente = sem filtro.
- `_filtros(f)` — {grupo: predicado}; as contagens de um grupo usam todos os outros.
- `_ordenar(itens, ordem)` — Ordena pelos campos na ordem dada; sem valor sempre por ultimo; empate final pelo appid.
- `api_promocoes(qs)` — Explorador da aba Promocoes: filtra, conta e pagina no Hunter (pensando na Steam inteira, spec 07).
- `api_vitrine(_q)` — Prateleiras de Ofertas → Destaques (antiga "Vale a pena"): um bloco por tipo (exclusivo), so jogos (sem DLCs), sem os que voce tem. O Selo vale com
- `_rar_info(an)` — O 'por que essa raridade' da ficha.
- `_estado_dlcs(b, a, j)` — Por que a ficha nao tem DLCs: falhou, a Steam nao informou ou ainda nao consultada (com a fila, se rodando).
- `api_jogo(q)`
- `_ficha_local(b, ctx, cfg, a, r)` — O que a ficha nova (spec 09) le junto, sem rede: a fileira da franquia e o tempo jogado.
- `api_jogo_extra(q)` — O que a ficha busca na rede ao abrir (descricao e captura, HLTB e notas, conquistas), com cache: vem depois
- `api_hltb(q)` — Tempo para zerar (HowLongToBeat, em minutos) dos jogos de uma franquia: ?appids=1,2,3 (até 60).
- `post_franquia(d)` — Troca a franquia do jogo a mao (juntar = escolher uma que existe; separar = nome novo); vazio volta ao automatico.
- `_jogo_steam(b, cfg, ctx, a)` — Ficha de um item da Steam inteira (fora da lista): o historico das lojas marcadas pela ITAD, baixado na hora
- `_ler_carrinho()`
- `_gravar_carrinho(itens)`
- `api_carrinho(_q)` — Carrinho simulado da Steam: jogos/DLCs e bundles (com o preco para voce). Jogo de outra loja nao entra: o painel abre a pagina da loja.
- `_modo(m)` — Como o item entra no carrinho da Steam: para a conta, de presente ou compra privada.
- `post_carrinho(d)` — O carrinho fica num arquivo proprio: gravar nele nunca espera a coleta liberar o banco.
- `api_buscar(q)` — Nome, appid ou link da Steam -> resultados da loja.
- `post_extra(d)` — Passa a monitorar um jogo fora da lista de desejos (ou para de monitorar).
- `api_biblioteca(_q)` — Visao de colecionador: valor da biblioteca, o que falta para completar cada jogo e as franquias.
- `_dlcs_em_promocao(b, cfg, ctx, jogos)` — DLCs que contam (relevantes), que voce nao tem, de jogos que voce tem, com desconto agora (spec 04, D5).
- `api_acesso(_q)`
- `post_acesso(d)`
- `post_tenho(d)` — Marca/desmarca "ja tenho" (para compras feitas depois do userdata.json).
- `post_silenciar(d)`
- `post_atualizar_tudo(_d)`
- `_itens_para_steam()` — Itens da Steam do carrinho do Hunter (pacote ou bundle) para mandar ao carrinho da conta; descobre na hora o pacote que falta.
- `post_atualizar_app(_d)`
- `post_sair(_d)`
- `api_notificacoes(_q)`
- `api_alertas(_q)`
- `api_config(_q)`
- `post_config(dados)`
- `post_telegram(d)` — Conecta o bot do Telegram (so pelo proprio PC). acao: token (guarda e testa), vincular (acha a conversa),
- `post_dlc(d)`
- `post_modo(d)`
- `post_verificar(_d)`
- `post_pausar(_d)`
- `post_steam_carrinho(_d)` — Monta o endereco do carrinho da Steam com o pedido (#kurokami=PAIS:p<subid>[-modo],b<bundleid>[-modo]).
- `_navegador_padrao()` — (nome, exe, pagina de extensoes) do navegador padrao do Windows, ou None se nao for um que a extensao aceita.
- `post_steam_extensao(d)` — Assistente da extensao do painel. No Edge padrao, abre a pagina dela na loja do Edge (um clique em Obter;
- `post_steam_conta(d)` — Dados da sua conta Steam que a extensao leu na loja, com a sessao da pagina (senha, token e cookie nunca chegam
- `_limpar_sessao_qr()` — O login por QR saiu na 0.16 (a Steam o tratava como celular novo). Quem tinha a sessao no cofre:
- `_log_erro(rota, e)`
- **class `Handler`** — 
  - `log_message()`
  - `_host_local()` — Host do cabecalho precisa ser o do proprio PC (barra DNS rebinding: um site com nome seu apontando para 127.0.0.1).
  - `_local()`
  - `_autorizado(u)` — Do proprio PC: sempre. De outro aparelho: so depois de digitar o PIN (fica lembrado por 1 ano).
  - `_pagina_pin(erro)`
  - `_entrar()`
  - `_pagina_dados(arquivo)` — Ofertas e Biblioteca: o modelo com os dados de agora dentro (gzip: ~3 MB viram ~400 KB no celular).
  - `_json(obj, code)`
  - `_steam_openid(u)` — Entrar pela Steam (OpenID). So pelo proprio PC: outro aparelho nao pode trocar a conta do Hunter.
  - `do_GET()`
  - `do_POST()`
- **class `_Servidor`** — 
- `iniciar(abrir)`
- `reiniciar()` — Troca entre so-este-PC e rede local sem fechar o Hunter.
- `url()`

## `radar/previsao.py`
Previsão de Ofertas (spec 09): "se eu não comprar agora, esse preço volta?", o piso de 24 meses e "quando e por

- `nome_ev(t)`
- `mm(t)`
- `brl(c)`
- `tol(p)` — Folga de centavos do "igual" (R$ 0,10 ou 1%).
- `dez(f)`
- `tempo(d)`
- `kc(k)`
- `grupo(tipo, k)` — Taxas do grupo (tipo × vezes nesse preço em 24 meses). Grupo com menos de 30 casos: na 1ª vez, junta todas as
- `eventos(linhas_steam, agora)` — Grandes eventos da Steam pelo próprio histórico: dias em que 200+ jogos começaram promoção (epoch, em ordem).
- **class `Previsor`** — Previsões num instante fixo (`agora`), com os eventos do último ano projetados para o próximo.
  - `evento_perto(t)`
  - `hist(lin)` — [[dias desde agora (negativo), duração em dias, menor preço, maior corte], ...] dos últimos 25 meses.
  - `prever(lin, p, corte, tipo, em_promo, fim)` — O que a página mostra: piso de 24 meses, risco (o preço não voltar em 3 meses), espera e a próxima promoção.

## `radar/progresso.py`
Em que parte da checagem o Hunter esta (para o painel e o icone da bandeja).

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
Pagina local com os alertas atuais. Abre no navegador.

- `gerar(alertas, capas, novos_ids)`

## `radar/series.py`
Agrupa jogos da mesma serie pelo nome, em vez do campo "franquia" da Steam

- `tokens(nome)`
- `chave(nome)`
- `rotulo(nomes)` — Prefixo comum dos nomes, recortado do primeiro nome original (mantem a grafia: "Half-Life", "Need for Speed").
- `agrupar(itens)` — itens: [{"appid", "nome", ...}] -> {chave: [itens]}
- `_editora(f)`
- `_limpa(f)`
- `_da_steam(it)`
- `franquias(itens, manual)` — itens: [{"appid", "nome", "franquia"}] -> {appid: nome da franquia}.

## `radar/servico.py`
O ciclo que roda sozinho: coleta -> avalia -> notifica, no intervalo do config.

- `criar_log(eco)`
- `_fim_iso(v)`
- `candidatos_fim(b, alertas, cfg)` — O que esta no carrinho ou "vale a pena" e tem data de fim conhecida (ITAD ou Steam).
- `ciclo(log, forcar, sem_limite, steam_agora)` — Uma rodada. forcar+sem_limite = verificacao completa. Devolve (alertas, novos).
- **class `Servico`** — 
  - `_precisa_completa()` — 1a checagem e sempre completa; depois, a cada N dias (config verificacao_completa_dias).
  - `agora(completo)`
  - `run()`

## `radar/steam.py`
Steam: lista de desejos, biblioteca, detalhes da loja, DLCs e opcoes de compra.

- `resolver_steamid(chave, perfil)` — SteamID64 a partir do perfil. Tenta primeiro sem chave (perfil publico, XML da comunidade).
- `perfil_publico(steamid)` — {"nome", "avatar"} do perfil (XML da comunidade, sem chave), para o icone no topo do painel. None se falhar.
- `wishlist(chave, steamid)`
- `biblioteca_api(chave, steamid)`
- `conquistas(chave, steamid, appid)` — Conquistas do jogo na conta (ficha, 1 chamada). Jogo sem conquistas: total 0. Perfil privado: erro 403.
- `detalhes_loja(appid, pais)` — O que a ficha mostra da pagina da loja (1 chamada, sem ritmo: e a pessoa abrindo a ficha, nunca em lote).
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

## `radar/steam_inteira.py`
Promocoes da Steam inteira (spec 07): IStoreQueryService/Query, sem chave, 1.000 itens por chamada.

- `_pedido(start, pais)`
- `_capa(it)`
- `normalizar(it)` — Item da Query -> linha de steam_promo, ou None se nao for compravel/sem desconto.
- `baixar(pais, max_chamadas)` — {appid: linha} de todas as promocoes da Steam. Levanta excecao se nao conseguir ler tudo.
- `_mapear(banco, chave, appids, log)` — {appid: gid} pela ITAD, guardado em promo_estado (gid '' = a ITAD nao conhece; tenta de novo em 30 dias).
- `_marcas(banco, chave, pais, novos, log)` — Preenche gid, flag, hl, hl1 de cada item. A marca e os menores ficam em promo_estado e so sao pedidos de novo
- `_aval(linhas, preco, corte, al)` — Avaliacao de um item com o historico das lojas marcadas, em JSON (como as linhas da lista); None se o dado
- `avaliar(banco, cfg, itens)` — Preenche it["aval"] (JSON) de cada item {appid: {preco, corte, flag}}: com historico, a mesma avaliacao da
- `coletar(banco, cfg, log, chave_itad)` — Baixa as promocoes, junta a marca e os menores da ITAD, avalia com o historico que ja tem e substitui o
- `_perto(r)` — Pode ser recorde (vale baixar o historico): marca da ITAD ou preco no menor de 1 ano.
- `historicos(banco, cfg, chave, log, por_rodada)` — Baixa o historico (lojas marcadas, pela ITAD) de quem esta perto do recorde, aos poucos (`por_rodada` jogos;
- `historico_um(banco, cfg, chave, appid, log)` — Ficha de um item da Steam inteira (o dono clicou nele): baixa o historico (lojas marcadas) na hora, se ainda

## `radar/steam_openid.py`
Entrar pela Steam (OpenID 2.0), como no ITAD, na GG.deals e na SteamDB.

- **class `LoginInvalido`** — 
- `_limpar(agora)`
- `_retorno(base, state)`
- `url_de_entrada(base)` — URL da pagina de login da Steam. `base` = http://localhost[:porta], montada pelo servidor (nunca pelo cabecalho Host).
- `_confirmar_na_steam(params)`
- `concluir(query, base, confirmar, agora)` — Valida a volta da Steam e devolve o SteamID (17 digitos). `query` = dict de listas (parse_qs).

## `radar/telegram.py`
Telegram (bot gratuito): espelha os avisos no celular, fora de casa.

- `_chamar(token, metodo, dados, timeout)` — Devolve (ok, resposta_json_ou_erro). Nunca levanta: aviso que falha nao pode derrubar a coleta.
- `_cfg(cfg)`
- `ligado(cfg)` — Ligado + token + conversa vinculada.
- `enviar(cfg, titulo, texto, botoes, foto)` — botoes: [(rotulo, url)]: so links https publicos (localhost e file:/// nao abrem no celular).
- `conectar(token)` — Testa o token (getMe). Devolve (ok, @usuario_do_bot ou mensagem de erro).
- `achar_conversa(token)` — Chat de quem mandou mensagem ao bot. Devolve (chat_id, nome) ou (None, motivo).

## `radar/validar.py`
Testa cada chave com uma chamada real e explica o resultado.

- `formato_suspeito(nome, chave)`
- `testar(nome, chave)` — (ok, mensagem)
- `testar_perfil(perfil)` — (ok, mensagem, steamid). Usa so dados publicos: nao precisa de chave.
