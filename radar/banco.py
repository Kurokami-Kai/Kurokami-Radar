"""SQLite local. Precos sao gravados so quando mudam, entao o historico
cresce devagar mesmo checando a cada 30 minutos."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from . import caminhos

ESQUEMA = """
CREATE TABLE IF NOT EXISTS jogo(
  appid INTEGER PRIMARY KEY, nome TEXT, tipo TEXT, pai INTEGER, capa TEXT,
  rpos INTEGER, rcount INTEGER, rotulo TEXT, lancamento INTEGER, em_breve INTEGER,
  gratis INTEGER DEFAULT 0, preco_steam INTEGER, cheio_steam INTEGER, desconto_steam INTEGER,
  na_lista INTEGER DEFAULT 0, possuido INTEGER DEFAULT 0, itad_id TEXT,
  atualizado TEXT);
CREATE TABLE IF NOT EXISTS dlc(
  appid INTEGER PRIMARY KEY, pai INTEGER, classe TEXT, origem TEXT DEFAULT 'auto');
CREATE INDEX IF NOT EXISTS dlc_pai ON dlc(pai);
CREATE TABLE IF NOT EXISTS opcao(
  id TEXT PRIMARY KEY, tipo TEXT, nome TEXT, final INTEGER, cheio INTEGER,
  desconto INTEGER, desconto_bundle INTEGER, itens TEXT, capa TEXT, atualizado TEXT);
CREATE TABLE IF NOT EXISTS jogo_opcao(appid INTEGER, opcao TEXT, PRIMARY KEY(appid, opcao));
CREATE TABLE IF NOT EXISTS preco(
  appid INTEGER, loja TEXT, preco INTEGER, cheio INTEGER, corte INTEGER,
  quando TEXT, fonte TEXT, url TEXT);
CREATE INDEX IF NOT EXISTS preco_idx ON preco(appid, loja, quando);
CREATE TABLE IF NOT EXISTS gg(
  appid INTEGER PRIMARY KEY, oficial INTEGER, keyshop INTEGER,
  hist_oficial INTEGER, hist_keyshop INTEGER, url TEXT, atualizado TEXT);
CREATE TABLE IF NOT EXISTS historico_importado(appid INTEGER PRIMARY KEY, quando TEXT);
CREATE TABLE IF NOT EXISTS alerta(
  id INTEGER PRIMARY KEY AUTOINCREMENT, appid INTEGER, loja TEXT, preco INTEGER,
  motivo TEXT, quando TEXT, enviado INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS meta(chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS oferta_atual(
  appid INTEGER, loja TEXT, preco INTEGER, cheio INTEGER, corte INTEGER, url TEXT,
  drm_steam INTEGER, flag TEXT, quando TEXT, PRIMARY KEY(appid, loja));
CREATE TABLE IF NOT EXISTS tenho_manual(appid INTEGER PRIMARY KEY, quando TEXT);
CREATE TABLE IF NOT EXISTS silenciado(appid INTEGER PRIMARY KEY, quando TEXT);
CREATE TABLE IF NOT EXISTS consulta_lenta(tipo TEXT, id INTEGER, quando TEXT, PRIMARY KEY(tipo, id));
-- spec 07: Steam inteira. So o retrato das promocoes de agora; cada coleta substitui tudo (sem historico).
CREATE TABLE IF NOT EXISTS steam_promo(
  appid INTEGER PRIMARY KEY, tipo TEXT, nome TEXT, pacote INTEGER, preco INTEGER, cheio INTEGER, corte INTEGER,
  fim INTEGER, rpos INTEGER, rcount INTEGER, rotulo TEXT, lancamento INTEGER, capa TEXT, visto TEXT);
DROP TABLE IF EXISTS steam_hist;
-- Steam inteira com historico (08/10, pedido do dono): id ITAD de cada item e o historico (lojas marcadas) so de
-- quem esta perto do recorde, baixado aos poucos (steam_inteira.historicos). O retrato acima continua substituido.
-- flag/hl/hl1: marca e menores da ITAD, guardados (so reconsulta quando o preco muda ou 1x por dia: cota da ITAD)
CREATE TABLE IF NOT EXISTS promo_estado(
  appid INTEGER PRIMARY KEY, gid TEXT, mapeado TEXT, baixado TEXT, preco_baixado INTEGER, visto TEXT,
  flag TEXT, hl INTEGER, hl1 INTEGER, menores_preco INTEGER, menores_quando TEXT);
CREATE TABLE IF NOT EXISTS promo_hist(
  appid INTEGER, loja TEXT, preco INTEGER, cheio INTEGER, corte INTEGER, quando TEXT, PRIMARY KEY(appid, loja, quando));
-- spec 09 (ficha nova): tempo jogado do GetOwnedGames (substituido a cada leitura da biblioteca), o que a ficha busca
-- ao abrir (appdetails, Augmented Steam, conquistas; JSON com validade por fonte) e a franquia trocada a mao
CREATE TABLE IF NOT EXISTS tempo_jogo(appid INTEGER PRIMARY KEY, minutos INTEGER, ultima INTEGER);
CREATE TABLE IF NOT EXISTS ficha_cache(appid INTEGER, fonte TEXT, dados TEXT, quando TEXT, PRIMARY KEY(appid, fonte));
CREATE TABLE IF NOT EXISTS franquia_manual(appid INTEGER PRIMARY KEY, nome TEXT, quando TEXT);
"""


def agora():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc(ts):
    """Tudo em UTC no mesmo formato, para a ordenacao por texto funcionar.
    (A ITAD manda horario com +02:00; misturado com +00:00 o 'ultimo preco' saia errado.)"""
    if not ts:
        return agora()
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except ValueError:
        return str(ts)


class Banco:
    def __init__(self, arquivo=None):
        caminhos.garantir()
        # timeout alto: o painel grava enquanto a coleta da bandeja tambem esta gravando
        self.con = sqlite3.connect(arquivo or caminhos.ARQ_BANCO, timeout=30)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(ESQUEMA)
        for sql in ("ALTER TABLE opcao ADD COLUMN papel TEXT",
                    "ALTER TABLE historico_importado ADD COLUMN escopo TEXT",
                    "ALTER TABLE jogo ADD COLUMN franquia TEXT",
                    "ALTER TABLE jogo ADD COLUMN menor_itad INTEGER",
                    "ALTER TABLE jogo ADD COLUMN capa_v TEXT",
                    "ALTER TABLE jogo ADD COLUMN fim_desconto INTEGER",
                    "ALTER TABLE jogo ADD COLUMN prioridade INTEGER",
                    "ALTER TABLE oferta_atual ADD COLUMN expira TEXT",
                    "ALTER TABLE jogo ADD COLUMN pacote INTEGER",
                    # Steam inteira: marca e menor de 1 ano da ITAD e a avaliacao (como as linhas da lista)
                    "ALTER TABLE steam_promo ADD COLUMN flag TEXT",
                    "ALTER TABLE steam_promo ADD COLUMN hl1 INTEGER",
                    "ALTER TABLE steam_promo ADD COLUMN aval TEXT",
                    # +18 (descritores de conteudo 3 e 4 da Steam): fica oculto nas Promocoes por padrao
                    "ALTER TABLE steam_promo ADD COLUMN adulto INTEGER"):
            try:
                self.con.execute(sql)
            except sqlite3.OperationalError:
                pass
        self._migrar()

    def _migrar(self):
        if (self.meta("esquema") or 1) >= 2:
            return
        # 1) preco lido direto da Steam vira uma "loja" propria: nao briga mais com o "Steam" da ITAD
        self.con.execute("UPDATE preco SET loja='Steam (direto)' WHERE fonte='steam'")
        # 2) horarios em UTC
        rows = self.con.execute("SELECT rowid, quando FROM preco WHERE quando NOT LIKE '%+00:00'").fetchall()
        self.con.executemany("UPDATE preco SET quando=? WHERE rowid=?", [(utc(q), r) for r, q in rows])
        # 3) apaga repeticoes criadas pela briga entre as duas leituras
        apagar, ant = [], {}
        for r in self.con.execute("SELECT rowid, appid, loja, preco, cheio, fonte FROM preco "
                                  "WHERE fonte!='itad-historico' ORDER BY appid, loja, quando"):
            k = (r[1], r[2])
            if k in ant and ant[k] == (r[3], r[4]):
                apagar.append((r[0],))
            ant[k] = (r[3], r[4])
        self.con.executemany("DELETE FROM preco WHERE rowid=?", apagar)
        self.meta("esquema", 2)
        self.con.commit()

    def commit(self):
        self.con.commit()

    def q(self, sql, *a):
        return self.con.execute(sql, a).fetchall()

    def um(self, sql, *a):
        return self.con.execute(sql, a).fetchone()

    # ---------------- meta
    def meta(self, chave, valor=None):
        if valor is None:
            r = self.um("SELECT valor FROM meta WHERE chave=?", chave)
            return json.loads(r["valor"]) if r else None
        self.con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (chave, json.dumps(valor)))

    # ---------------- jogos
    def salvar_jogo(self, j):
        cols = ["appid", "nome", "tipo", "pai", "capa", "rpos", "rcount", "rotulo", "lancamento",
                "em_breve", "gratis", "preco_steam", "cheio_steam", "desconto_steam", "franquia", "capa_v", "pacote"]
        # fim do desconto: substitui mesmo quando vem vazio (promocao acabou)
        if "fim_desconto" in j:
            self.con.execute("INSERT INTO jogo(appid) VALUES(?) ON CONFLICT(appid) DO NOTHING", (j["appid"],))
            self.con.execute("UPDATE jogo SET fim_desconto=? WHERE appid=?", (j["fim_desconto"], j["appid"]))
        vals = [j.get(c) for c in cols]
        self.con.execute(
            "INSERT INTO jogo(%s, atualizado) VALUES(%s, ?) ON CONFLICT(appid) DO UPDATE SET %s, atualizado=excluded.atualizado"
            % (",".join(cols), ",".join("?" * len(cols)),
               ",".join("%s=COALESCE(excluded.%s, %s)" % (c, c, c) for c in cols[1:])),
            vals + [agora()])

    def marcar_listas(self, wishlist, possuidos, prioridade=None):
        # o que voce marcou como "ja tenho" no painel conta como seu
        possuidos = list(possuidos) + [r["appid"] for r in self.q("SELECT appid FROM tenho_manual")]
        self.con.execute("UPDATE jogo SET na_lista=0, possuido=0, prioridade=NULL")
        self.con.executemany("INSERT INTO jogo(appid, na_lista) VALUES(?,1) ON CONFLICT(appid) DO UPDATE SET na_lista=1",
                             [(a,) for a in wishlist])
        self.con.executemany("INSERT INTO jogo(appid, possuido) VALUES(?,1) ON CONFLICT(appid) DO UPDATE SET possuido=1",
                             [(a,) for a in possuidos])
        if prioridade:
            self.con.executemany("UPDATE jogo SET prioridade=? WHERE appid=?", [(p, a) for a, p in prioridade.items()])

    def salvar_tempo_jogo(self, tempos):
        """tempos: {appid: (minutos, ultima_unix)} da ultima leitura da biblioteca; substitui tudo."""
        self.con.execute("DELETE FROM tempo_jogo")
        self.con.executemany("INSERT INTO tempo_jogo VALUES(?,?,?)", [(a, m, u) for a, (m, u) in tempos.items()])

    def definir_itad(self, appid, gid):
        self.con.execute("UPDATE jogo SET itad_id=? WHERE appid=?", (gid, appid))

    # ---------------- dlcs
    def salvar_dlc(self, appid, pai, classe):
        # nunca sobrescreve uma classificacao feita pelo usuario
        self.con.execute(
            "INSERT INTO dlc(appid, pai, classe) VALUES(?,?,?) ON CONFLICT(appid) DO UPDATE SET pai=excluded.pai, "
            "classe=CASE WHEN dlc.origem='usuario' THEN dlc.classe ELSE excluded.classe END", (appid, pai, classe))

    # ---------------- opcoes (bundles e edicoes)
    def salvar_opcao(self, o):
        self.con.execute(
            "INSERT OR REPLACE INTO opcao(id, tipo, nome, final, cheio, desconto, desconto_bundle, itens, capa, atualizado, papel) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (o["id"], o["tipo"], o["nome"], o["final"], o["cheio"], o["desconto"], o.get("desconto_bundle"),
             json.dumps(o["itens"]), o.get("capa"), agora(), o.get("papel")))

    def itens_opcao(self, oid):
        r = self.um("SELECT itens FROM opcao WHERE id=?", oid)
        return json.loads(r["itens"]) if r else None

    def consultado(self, tipo, ident, dias):
        r = self.um("SELECT quando FROM consulta_lenta WHERE tipo=? AND id=?", tipo, ident)
        if not r:
            return False
        return (datetime.now(timezone.utc) - datetime.fromisoformat(r["quando"])).days < dias

    def marcar_consulta(self, tipo, ident):
        self.con.execute("INSERT OR REPLACE INTO consulta_lenta VALUES(?,?,?)", (tipo, ident, agora()))

    def ultima_consulta(self, tipo, ident):
        r = self.um("SELECT quando FROM consulta_lenta WHERE tipo=? AND id=?", tipo, ident)
        return r["quando"] if r else None

    def limpar_consulta(self, tipo, ident):
        self.con.execute("DELETE FROM consulta_lenta WHERE tipo=? AND id=?", (tipo, ident))

    def ligar_opcao(self, appid, oid):
        self.con.execute("INSERT OR IGNORE INTO jogo_opcao VALUES(?,?)", (appid, oid))

    # ---------------- precos
    def registrar_preco(self, appid, loja, preco, cheio, corte, fonte, url=None, quando=None):
        """Grava so se mudou desde o ultimo registro dessa loja."""
        if preco is None:
            return False
        ult = self.um("SELECT preco, cheio FROM preco WHERE appid=? AND loja=? ORDER BY quando DESC LIMIT 1", appid, loja)
        if ult and ult["preco"] == preco and (ult["cheio"] == cheio or cheio is None):
            return False
        self.con.execute("INSERT INTO preco VALUES(?,?,?,?,?,?,?,?)",
                         (appid, loja, preco, cheio, corte, utc(quando) if quando else agora(), fonte, url))
        return True

    def importar_historico(self, appid, registros):
        """registros: [(loja, preco, cheio, corte, quando)] vindos da ITAD."""
        # reimportacao (ex.: antes eram so as lojas marcadas) substitui o que veio antes, sem duplicar
        self.con.execute("DELETE FROM preco WHERE appid=? AND fonte='itad-historico'", (appid,))
        self.con.executemany(
            "INSERT INTO preco(appid, loja, preco, cheio, corte, quando, fonte) VALUES(?,?,?,?,?,?,'itad-historico')",
            [(appid, r[0], r[1], r[2], r[3], utc(r[4])) for r in registros if r[1] is not None])
        self.con.execute("INSERT OR REPLACE INTO historico_importado(appid, quando, escopo) VALUES(?,?,'todas')",
                         (appid, agora()))

    def menor(self, appid, lojas=None, dias=None):
        """Menor preco registrado. dias: so olha essa janela (0/None = desde sempre).
        Precos que estavam valendo no inicio da janela tambem contam."""
        filtro, args = "", [appid]
        if lojas:
            filtro += " AND loja IN (%s)" % ",".join("?" * len(lojas))
            args += list(lojas)
        if dias:
            desde = (datetime.now(timezone.utc) - timedelta(days=dias)).replace(microsecond=0).isoformat()
            r = self.um("SELECT MIN(preco) m FROM preco WHERE appid=?%s AND quando>=?" % filtro, *(args + [desde]))
            vigente = self.um("""SELECT MIN(p.preco) m FROM preco p JOIN (SELECT loja, MAX(quando) mq FROM preco
                                 WHERE appid=?%s AND quando<? GROUP BY loja) u ON p.loja=u.loja AND p.quando=u.mq
                                 WHERE p.appid=?""" % filtro, *(args + [desde, appid]))
            vals = [x for x in ((r or {})["m"] if r else None, (vigente or {})["m"] if vigente else None) if x is not None]
            return min(vals) if vals else None
        r = self.um("SELECT MIN(preco) m FROM preco WHERE appid=?%s" % filtro, *args)
        return r["m"] if r else None

    def linhas_lote(self, lojas, appids=None):
        """{appid: [registros de preco em ordem]} das lojas dadas, para a lista inteira (ou os appids dados)."""
        if not lojas:
            return {}
        filtro = ("(SELECT appid FROM jogo WHERE na_lista=1)" if appids is None
                  else "(%s)" % ",".join(str(int(a)) for a in appids))
        rows = self.q("SELECT appid, loja, preco, corte, quando FROM preco WHERE loja IN (%s) AND appid IN %s ORDER BY appid, quando"
                      % (",".join("?" * len(lojas)), filtro), *lojas)
        por = {}
        for r in rows:
            por.setdefault(r["appid"], []).append(r)
        return por

    def pisos_lote(self, lojas, janelas=(90, 180, 270, 365)):
        """Igual a pisos(), para todos os jogos da lista de uma vez."""
        return {a: self._pisos_de(rs, janelas) for a, rs in self.linhas_lote(lojas).items()}

    @staticmethod
    def _pisos_de(rows, janelas):
        # brindes (R$ 0, ex.: Half-Life de graca no aniversario) nao sao "preco": ficam fora do piso
        rows = [r for r in rows if r["preco"]] or rows
        if not rows:
            return {}
        agora_ = datetime.now(timezone.utc)
        out = {0: min(r["preco"] for r in rows),
               "dias": (agora_ - datetime.fromisoformat(min(r["quando"] for r in rows))).days}
        for d in janelas:
            desde = (agora_ - timedelta(days=d)).replace(microsecond=0).isoformat()
            vig = {}
            dentro = []
            for r in rows:
                if r["quando"] >= desde:
                    dentro.append(r["preco"])
                else:
                    vig[r["loja"]] = r["preco"]
            vals = dentro + list(vig.values())
            out[d] = min(vals) if vals else None
        return out

    def pisos(self, appid, lojas, janelas=(90, 180, 270, 365)):
        """{dias: menor preco na janela, 0: menor de todos os tempos} considerando so as lojas dadas.
        O preco que estava valendo quando a janela comecou tambem conta."""
        if not lojas:
            return {}
        rows = self.q("SELECT loja, preco, quando FROM preco WHERE appid=? AND loja IN (%s) ORDER BY quando"
                      % ",".join("?" * len(lojas)), appid, *lojas)
        return self._pisos_de(rows, janelas) if rows else {}

    def atuais(self, appid):
        """Ultimo preco de cada loja."""
        return self.q("""SELECT p.* FROM preco p JOIN (SELECT loja, MAX(quando) mq FROM preco WHERE appid=? GROUP BY loja) u
                         ON p.loja=u.loja AND p.quando=u.mq WHERE p.appid=?""", appid, appid)

    def salvar_ofertas_atuais(self, ofertas):
        """O que as lojas vendem AGORA (ultima resposta da ITAD). O historico nao serve para isso:
        se uma loja parou de vender o jogo, o ultimo registro dela pode ter anos (ex.: ARK gratis na Steam em 2022)."""
        q = agora()
        self.con.execute("DELETE FROM oferta_atual")
        self.con.executemany("INSERT OR REPLACE INTO oferta_atual(appid, loja, preco, cheio, corte, url, drm_steam, flag, quando, expira) "
                             "VALUES(?,?,?,?,?,?,?,?,?,?)",
                             [(a, o["loja"], o["preco"], o.get("cheio"), o.get("corte"), o.get("url"),
                               1 if o.get("drm_steam") else 0, o.get("flag"), q, o.get("expira"))
                              for a, lst in ofertas.items() for o in lst if o.get("preco") is not None])

    def ofertas_atuais(self, appids=None):
        """{appid: [oferta]} vigentes, com a Steam lida direto do catalogo quando a ITAD nao traz a Steam."""
        filtro = "" if appids is None else " WHERE appid IN (%s)" % ",".join(str(int(a)) for a in appids)
        out = {}
        for r in self.q("SELECT * FROM oferta_atual" + filtro):
            out.setdefault(r["appid"], []).append(dict(r))
        jf = "WHERE na_lista=1" if appids is None else "WHERE appid IN (%s)" % ",".join(str(int(a)) for a in appids)
        for j in self.q("SELECT appid, preco_steam, cheio_steam, desconto_steam FROM jogo " + jf):
            lst = out.setdefault(j["appid"], [])
            if j["preco_steam"] is not None and not any(o["loja"] == "Steam" for o in lst):
                lst.append({"appid": j["appid"], "loja": "Steam", "preco": j["preco_steam"], "cheio": j["cheio_steam"],
                            "corte": j["desconto_steam"] or 0, "url": None, "drm_steam": 1, "flag": None, "fonte": "catalogo"})
        return out

    def salvar_gg(self, appid, g):
        self.con.execute("INSERT OR REPLACE INTO gg VALUES(?,?,?,?,?,?,?)",
                         (appid, g.get("oficial"), g.get("keyshop"), g.get("hist_oficial"),
                          g.get("hist_keyshop"), g.get("url"), agora()))
