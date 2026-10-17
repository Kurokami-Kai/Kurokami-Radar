"""Metas para jogar mais (aba Status > Progresso): contra a "sindrome do PC gamer" (comprar e nao jogar).
Duas metas, ambas opcionais (0 = desligada), em `config["metas"]`:
- `horas_dia`: jogar X horas por dia. As horas vem de `horas_dia` (a diferenca de tempo jogado entre duas leituras da biblioteca,
  `Banco.salvar_tempo_jogo`), no dia local. Com `farm_cartas` ligado, jogo de farm (`jogados.farmados`) nao conta.
- `terminar_qtd` por `terminar_por` (semana, mes, ano): platinar N jogos (`terminado`, preenchida por `Banco.salvar_conquistas`
  quando um jogo passa a ter todas as conquistas). Conta daqui para a frente: o que ja estava platinado nao entra.
Ao bater uma meta: aviso do Windows/Telegram (`Notificador._avisar`, 1x por dia ou periodo) e um aviso guardado em
`meta["metas_pendentes"]` que o painel mostra num pop-up e apaga (`/api/metas_visto`)."""
from datetime import date, datetime, timedelta

PADRAO = {"horas_dia": 0, "terminar_qtd": 0, "terminar_por": "mes"}
PERIODOS = ("semana", "mes", "ano")


def normalizar(m):
    """A meta que veio do painel, limpa: horas de 0 a 24 (passo de 0,25), jogos de 0 a 99, periodo valido."""
    m = m if isinstance(m, dict) else {}
    try:
        h = round(min(24.0, max(0.0, float(m.get("horas_dia") or 0))) * 4) / 4
    except (TypeError, ValueError):
        h = 0
    try:
        q = min(99, max(0, int(m.get("terminar_qtd") or 0)))
    except (TypeError, ValueError):
        q = 0
    por = m.get("terminar_por") if m.get("terminar_por") in PERIODOS else "mes"
    return {"horas_dia": h, "terminar_qtd": q, "terminar_por": por}


def _config(cfg):
    return normalizar({**PADRAO, **(cfg.get("metas") or {})})


def _inicio(por, hoje):
    if por == "semana":
        return hoje - timedelta(days=hoje.weekday())
    return date(hoje.year, 1 if por == "ano" else hoje.month, 1)


def _chave(por, hoje):
    if por == "semana":
        a, s, _ = hoje.isocalendar()
        return "%d-S%02d" % (a, s)
    return str(hoje.year) if por == "ano" else "%d-%02d" % (hoje.year, hoje.month)


def _por_dia(b, cfg, desde):
    """{dia ISO: minutos} desde `desde`, sem os jogos de farm de cartas (se a opcao estiver ligada)."""
    farm = set()
    if cfg.get("farm_cartas"):
        from . import jogados
        farm = jogados.farmados(b)
    out = {}
    for r in b.q("SELECT dia, appid, minutos FROM horas_dia WHERE dia>=?", desde.isoformat()):
        if r["appid"] not in farm:
            out[r["dia"]] = out.get(r["dia"], 0) + (r["minutos"] or 0)
    return out


def _data_local(iso):
    try:
        return datetime.fromisoformat(iso).astimezone().date()
    except (TypeError, ValueError):
        return None


def _terminados(b, desde):
    """Jogos platinados desde `desde` (dia local), do mais novo ao mais antigo: [{appid, nome, quando}]."""
    out = []
    for r in b.q("""SELECT t.appid, j.nome, t.quando FROM terminado t LEFT JOIN jogo j ON j.appid=t.appid ORDER BY t.quando DESC"""):
        d = _data_local(r["quando"])
        if d and d >= desde:
            out.append({"appid": r["appid"], "nome": r["nome"] or str(r["appid"]), "quando": r["quando"]})
    return out


def resumo(b, cfg, hoje=None):
    """O que o painel mostra: a meta, o de hoje, os ultimos 14 dias, a sequencia de dias batendo a meta e os platinados do periodo."""
    hoje = hoje or datetime.now().date()
    m = _config(cfg)
    dias = _por_dia(b, cfg, hoje - timedelta(days=59))
    alvo = round(m["horas_dia"] * 60)
    ult = [{"dia": (hoje - timedelta(days=i)).isoformat(), "min": dias.get((hoje - timedelta(days=i)).isoformat(), 0)}
           for i in range(13, -1, -1)]
    seq, d = 0, hoje
    if alvo and dias.get(d.isoformat(), 0) < alvo:
        d -= timedelta(days=1)   # hoje ainda pode bater: a sequencia conta a partir de ontem
    while alvo and dias.get(d.isoformat(), 0) >= alvo and seq < 60:
        seq += 1
        d -= timedelta(days=1)
    ini = _inicio(m["terminar_por"], hoje)
    fim = _terminados(b, ini)
    return {"meta": m, "hoje": dias.get(hoje.isoformat(), 0), "dias": ult, "sequencia": seq,
            "terminados": fim, "desde": ini.isoformat(), "farm": bool(cfg.get("farm_cartas")),
            "base": b.um("SELECT COUNT(*) n FROM horas_dia")["n"] > 0}


def _pendente(b, tipo, titulo, texto):
    p = b.meta("metas_pendentes") or []
    p.append({"tipo": tipo, "titulo": titulo, "texto": texto})
    b.meta("metas_pendentes", p[-5:])


def avaliar(b, cfg, log=print, hoje=None):
    """Confere as metas e avisa as que acabaram de ser batidas (1x por dia / por periodo). Devolve os avisos novos."""
    hoje = hoje or datetime.now().date()
    m = _config(cfg)
    if not (m["horas_dia"] or m["terminar_qtd"]):
        return []
    r = resumo(b, cfg, hoje)
    avisados = b.meta("metas_avisos") or {}
    novos = []
    if m["horas_dia"] and r["hoje"] >= round(m["horas_dia"] * 60) and avisados.get("horas_dia") != hoje.isoformat():
        h = r["hoje"] / 60
        t = "Meta do dia batida: %s h" % (("%.1f" % h).replace(".", ",") if h < 10 else round(h))
        x = "Você jogou %s h hoje (meta: %s h)%s." % (("%.1f" % h).replace(".", ","), ("%g" % m["horas_dia"]).replace(".", ","),
                                                     " · %d dias seguidos" % r["sequencia"] if r["sequencia"] > 1 else "")
        avisados["horas_dia"] = hoje.isoformat()
        novos.append(("horas_dia", t, x))
    ch = _chave(m["terminar_por"], hoje)
    if m["terminar_qtd"] and len(r["terminados"]) >= m["terminar_qtd"] and avisados.get("terminar") != ch:
        por = {"semana": "da semana", "mes": "do mês", "ano": "do ano"}[m["terminar_por"]]
        avisados["terminar"] = ch
        novos.append(("terminar", "Meta %s batida: %d jogo(s) platinado(s)" % (por, len(r["terminados"])),
                      ", ".join(x["nome"] for x in r["terminados"][:4])))
    if not novos:
        return []
    b.meta("metas_avisos", avisados)
    for tipo, t, x in novos:
        _pendente(b, tipo, t, x)
    b.commit()
    try:
        from .notificador import Notificador, em_silencio
        from . import painel
        if not em_silencio(cfg) and not b.meta("pausado"):
            n = Notificador(b, cfg, log)
            for tipo, t, x in novos:
                n._avisar(t, x, clique=painel.url() + "#prog")
    except Exception as e:   # o pop-up do painel continua valendo
        log("Aviso de meta falhou: %s" % e)
    log("Metas batidas: %s" % ", ".join(n[0] for n in novos))
    return novos


def pegar_pendentes(b, vistos=0):
    """Os avisos que o pop-up ainda nao mostrou; `vistos` > 0 apaga os `vistos` primeiros (um aviso novo, chegado entre
    a leitura e a confirmacao do painel, fica)."""
    p = b.meta("metas_pendentes") or []
    if vistos and p:
        p = p[vistos:]
        b.meta("metas_pendentes", p)
        b.commit()
    return p
