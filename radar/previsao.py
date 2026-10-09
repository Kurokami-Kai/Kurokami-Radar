"""Previsão de Ofertas (spec 09): "se eu não comprar agora, esse preço volta?", o piso de 24 meses e "quando e por
quanto vem a próxima promoção". Mesma conta das amostras 6 a 8 (dados/dados_ofertas6.py), calibrada pelo backtest
(tools/backtest_previsao.py). TABELA é o resultado do backtest no histórico do dono (só taxas agregadas); recalcular
pelo histórico de cada usuário fica em docs/pendencias.md."""
import statistics
import time
from collections import Counter

from . import analise

DIA = 86400.0
MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

# backtest de 09/10/2026 (699 jogos da lista, 12.849 promoções): grupo "tipo|vezes nesse preço em 24 meses" ->
# n e a fração em que o preço voltou em 30/90/180/365 dias (mediana da espera em dias); concordância das 6 últimas
# promoções (concU), faixa das 3 últimas (faixa3) e o que vem depois de um preço novo (patamar)
TABELA = {
    "grupos": {
        "selo|0": {"n": 45, "f30": 0.2, "f90": 0.4667, "f180": 0.6222, "f365": 0.6667, "mediana": 132.7511},
        "novo|0": {"n": 798, "f30": 0.3772, "f90": 0.7406, "f180": 0.8446, "f365": 0.8935, "mediana": 41.2177},
        "igual|0": {"n": 15, "f30": 0.2667, "f90": 0.6, "f180": 0.7333, "f365": 0.8, "mediana": 53.5834},
        "igual|1": {"n": 604, "f30": 0.4023, "f90": 0.8477, "f180": 0.9305, "f365": 0.9603, "mediana": 34.9978},
        "igual|2-3": {"n": 822, "f30": 0.4428, "f90": 0.8479, "f180": 0.9234, "f365": 0.944, "mediana": 32.1275},
        "igual|4+": {"n": 2419, "f30": 0.537, "f90": 0.921, "f180": 0.9673, "f365": 0.9744, "mediana": 27.7295},
        "24m|0": {"n": 27, "f30": 0.2963, "f90": 0.7407, "f180": 0.7407, "f365": 0.8148, "mediana": 44.0421},
        "24m|2-3": {"n": 27, "f30": 0.4444, "f90": 0.8889, "f180": 0.963, "f365": 1.0, "mediana": 32.9687},
        "24m|4+": {"n": 308, "f30": 0.5779, "f90": 0.9286, "f180": 0.9643, "f365": 0.9675, "mediana": 24.0806},
        "nenhum|0": {"n": 26, "f30": 0.5385, "f90": 0.8846, "f180": 0.9231, "f365": 0.9615, "mediana": 29.8801},
        "nenhum|1": {"n": 182, "f30": 0.4231, "f90": 0.7912, "f180": 0.8901, "f365": 0.9615, "mediana": 37.0422},
        "nenhum|2-3": {"n": 482, "f30": 0.4793, "f90": 0.8133, "f180": 0.9087, "f365": 0.9564, "mediana": 31.9677},
        "nenhum|4+": {"n": 4957, "f30": 0.6183, "f90": 0.9167, "f180": 0.9641, "f365": 0.9756, "mediana": 22.9639}},
    "primeira80": {"n": 155, "f90": 0.5613, "f365": 0.729, "mediana": 52.9693},
    "concU": {"poucas": 0.5297, "1": 0.4068, "2": 0.5197, "3": 0.6116, "4": 0.6768, "5": 0.7732, "6": 0.8849},
    "faixa3": 0.8252,
    "patamar": {"todos": {"n": 653, "repetiu": 0.51, "caiu": 0.1103, "entre": 0.1547, "voltou": 0.2251},
                "24m": {"n": 44, "repetiu": 0.5, "caiu": 0.0455, "entre": 0.0909, "voltou": 0.3636}},
}


def nome_ev(t):
    m = time.gmtime(t).tm_mon
    s = 'Inverno' if m in (12, 1) else 'Primavera' if m in (2, 3, 4) else 'Verão' if m in (5, 6, 7) else 'Outono'
    return 'Promoção de %s da Steam' % s


def mm(t):
    return '%s/%d' % (MES[time.gmtime(t).tm_mon - 1], time.gmtime(t).tm_year)


def brl(c):
    return ('R$ %.2f' % (c / 100)).replace('.', ',')


def tol(p):
    """Folga de centavos do "igual" (R$ 0,10 ou 1%)."""
    return max(10, p * 0.01)


def dez(f):
    return 'quase 10' if f >= .95 else str(max(0, min(9, round(f * 10))))


def tempo(d):
    if d < 10:
        return 'poucos dias'
    if d < 45:
        return '~%d semanas' % max(2, round(d / 7))
    return '~%d meses' % max(2, round(d / 30.4))


def kc(k):
    return '0' if k == 0 else '1' if k == 1 else '2-3' if k <= 3 else '4+'


def grupo(tipo, k):
    """Taxas do grupo (tipo × vezes nesse preço em 24 meses). Grupo com menos de 30 casos: na 1ª vez, junta todas as
    1ª vezes fora o Selo; senão, o tipo inteiro."""
    G = TABELA["grupos"]
    g = G.get('%s|%s' % (tipo, kc(k)))
    if g and g['n'] >= 30:
        return g
    sub = ([v for kk, v in G.items() if kk.endswith('|0') and not kk.startswith('selo|')] if k == 0 and tipo != 'selo'
           else [v for kk, v in G.items() if kk.startswith(tipo + '|')])
    if not sub:
        return None
    n = sum(v['n'] for v in sub)
    return {'n': n, **{c: sum(v[c] * v['n'] for v in sub) / n for c in ('f30', 'f90', 'f180', 'f365', 'mediana')}}


def eventos(linhas_steam, agora):
    """Grandes eventos da Steam pelo próprio histórico: dias em que 200+ jogos começaram promoção (epoch, em ordem)."""
    c = Counter()
    for lin in linhas_steam:
        for ini, _f, _c in analise.episodios(analise.linha_do_tempo(lin, agora)):
            c[int(ini // DIA)] += 1
    ev = []
    for d in sorted(d for d, n in c.items() if n >= 200):
        if not ev or d - ev[-1] > 3:
            ev.append(d)
    return [d * DIA for d in ev]


class Previsor:
    """Previsões num instante fixo (`agora`), com os eventos do último ano projetados para o próximo."""

    def __init__(self, agora, ev):
        self.agora = agora
        prox = sorted((t + 364 * DIA, t) for t in ev if agora - 365 * DIA <= t < agora)
        self.prox = [(n, o) for n, o in prox if n > agora + 3 * DIA]

    def evento_perto(self, t):
        for n, _o in self.prox:
            if abs(n - t) <= 25 * DIA:
                return n
        return None

    def hist(self, lin):
        """[[dias desde agora (negativo), duração em dias, menor preço, maior corte], ...] dos últimos 25 meses."""
        AGORA = self.agora
        segs = analise.linha_do_tempo(lin, AGORA)
        out = []
        for ini, fim, mc in analise.episodios(segs):
            if fim < AGORA - 760 * DIA:
                continue
            v = [sg[2] for sg in segs if sg[2] and sg[0] < fim and sg[1] > ini and sg[3] > 0]
            if v:
                out.append([round((ini - AGORA) / DIA), max(1, round((fim - ini) / DIA)), min(v), mc])
        return out

    def prever(self, lin, p, corte, tipo, em_promo, fim):
        """O que a página mostra: piso de 24 meses, risco (o preço não voltar em 3 meses), espera e a próxima promoção.
        A promoção de agora entra na série da próxima; um preço novo vira o patamar provável (sexta rodada)."""
        AGORA, PROX, PAT = self.agora, self.prox, TABELA["patamar"]
        segs = analise.linha_do_tempo(lin, AGORA)
        if not segs:
            return None
        eps = analise.episodios(segs)
        pe = []
        for e in eps:
            v = [s[2] for s in segs if s[2] and s[0] < e[1] and s[1] > e[0] and s[3] > 0]
            pe.append(min(v) if v else None)
        atual = eps[-1] if em_promo and eps and eps[-1][1] >= AGORA - 1 else None
        past = [(e, q) for e, q in zip(eps, pe) if q and (not atual or e[1] < atual[0])]
        out = {'desde': mm(segs[0][0])}
        if past:
            mn = min(past, key=lambda x: (x[1], -x[0][0]))
            out['menor'] = [mn[1], mm(mn[0][0])]
        # piso dos últimos 24 meses (antes desta), quantas vezes veio e quando deve voltar
        ref_t = atual[0] if atual else AGORA
        p24 = [(e, q) for e, q in past if e[0] >= ref_t - 730 * DIA]
        if p24:
            pz = min(q for _e, q in p24)
            vz = [e for e, q in p24 if q <= pz + tol(pz)]
            out['piso'] = [pz, len(vz), mm(vz[-1][0])]
            gz = [(b[0] - a[0]) / DIA for a, b in zip(vz, vz[1:])]
            if gz:
                g = statistics.median(gz[-6:])
                nx = vz[-1][0] + g * DIA
                ref = (fim if atual and fim and fim > AGORA else AGORA) + 7 * DIA
                while nx < ref:
                    nx += g * DIA
                out['piso_volta'] = round((nx - AGORA) / DIA)
        # ---------------- está em promoção: "se você não comprar agora"
        if em_promo and p is not None:
            lim = p + tol(p)
            ok = [(e, q) for e, q in past if q <= lim]
            k24 = sum(1 for e, _ in ok if e[0] >= AGORA - 730 * DIA)
            g = grupo(tipo or 'nenhum', k24)
            risco = 1 - g['f90'] if g else None
            P80 = TABELA["primeira80"]
            if risco is not None and k24 == 0 and corte >= 80 and P80:
                risco = max(risco, 1 - P80['f90'])
                g = dict(g, f90=P80['f90'], f365=P80['f365'], mediana=P80['mediana'], n=P80['n'])
            fim_t = fim if fim and fim > AGORA else AGORA
            gaps = [(b[0][0] - a[0][0]) / DIA for a, b in zip(ok, ok[1:])][-6:]
            if k24 >= 2 and gaps:
                espera = max(7, statistics.median(gaps) - 10)
                base = 'esse preço (ou menor) apareceu %d vezes nos últimos 2 anos, a cada %s (a última em %s)' % (
                    k24, tempo(statistics.median(gaps)), mm(ok[-1][0][0]))
            else:
                espera = g['mediana'] if g else None
                base = ('esse preço apareceu 1 vez nos últimos 2 anos (%s)' % mm([e for e, _ in ok][-1][0]) if k24 == 1 else
                        'é a primeira vez nesse preço em 2 anos' if past else 'é a primeira promoção registrada nas suas lojas')
            quando = None
            if espera is not None and espera < 900:
                t_v = fim_t + espera * DIA
                ev = self.evento_perto(t_v)
                quando = ('na %s (%s)' % (nome_ev(ev), mm(ev))) if ev else 'por volta de %s' % mm(t_v)
            l1 = base[0].upper() + base[1:] + '.'
            if g:
                l2 = 'Em %d casos assim no seu histórico, %s em 10 voltaram em até 3 meses e %s em 10 em até 1 ano.' % (
                    g['n'], dez(g['f90']), dez(g['f365']))
                if quando:
                    l2 += ' Deve voltar %s.' % quando if risco < 0.4 else ' Se voltar, o mais provável é %s.' % quando
            else:
                l2 = ''
            out.update(risco=round(risco, 3) if risco is not None else None, espera=round(espera) if espera else None,
                       k24=k24, se1=l1, se2=l2)
        # ---------------- a próxima promoção (para quem está fora; e a que vem depois desta)
        serie = past + ([(atual, p)] if atual and p is not None else [])
        if len(serie) >= 2:
            starts = [e[0] for e, _ in serie]
            gaps = [b - a for a, b in zip(starts, starts[1:])][-6:]
            r1 = starts[-1] + statistics.median(gaps)
            ref = (fim if (atual and fim and fim > AGORA) else AGORA) + 7 * DIA
            while r1 < ref:
                r1 += statistics.median(gaps)
            esteve = [n for n, o in PROX if any(abs(e[0] - o) <= 4 * DIA for e, _ in serie)]
            r2 = esteve[0] if esteve else None
            t_n = min(r1, r2) if r2 else r1
            ult = serie[-1][1]
            ult6 = [q for _e, q in serie[-6:]]
            conc = sum(abs(v - ult) <= tol(ult) for v in ult6) if len(ult6) == 6 else 0   # com menos de 6: faixa
            c_ult = corte if atual else serie[-1][0][2]
            ant = [q for _e, q in serie[:-1]]
            pat = None
            if atual and ant:      # preço novo, 10%+ abaixo (de sempre ou dos 24 meses): o backtest mede se vira o patamar
                ant24 = [q for e, q in serie[:-1] if e[0] >= atual[0] - 730 * DIA]
                pat = ('todos' if p <= 0.9 * min(ant) else
                       '24m' if p >= min(ant) - tol(min(ant)) and ant24 and p <= 0.9 * min(ant24) else None)
            if pat:
                x = PAT[pat]
                preco = 'provavelmente %s de novo (-%d%%): é um preço novo%s, e depois de um assim a próxima repetiu esse preço (ou menor) em %s de 10 casos' % (
                    brl(p), corte, '' if pat == 'todos' else ' nos últimos 2 anos', dez(x['repetiu'] + x['caiu']))
                conf = 'voltou ao preço de antes (~%s) em %s de 10 (%d casos no seu histórico)' % (
                    brl(statistics.median(ant[-3:])), dez(x['voltou']), x['n'])
                conc = 4
            elif conc >= 4:
                preco = 'provavelmente %s (-%d%%), o preço de %d das 6 últimas promoções' % (brl(ult), c_ult, conc)
                conf = 'a próxima repetiu esse preço em %s de 10 casos assim' % dez(TABELA["concU"].get(str(conc), .7))
            else:
                u3 = [q for _e, q in serie[-3:]]
                preco = 'entre %s e %s (as 3 últimas variaram)' % (brl(min(u3)), brl(max(u3)))
                conf = 'a próxima ficou nessa faixa em %s de 10 casos' % dez(TABELA["faixa3"])
            if t_n == r2:
                quando = 'na %s (%s), em que esteve no ano passado' % (nome_ev(r2), mm(r2))
            else:
                quando = 'por volta de %s (costuma entrar a cada %s)' % (mm(t_n), tempo(statistics.median(gaps) / DIA))
            mes = MES[time.gmtime(t_n).tm_mon - 1] + '/' + str(time.gmtime(t_n).tm_year)[2:]
            out.update(prox1='%s, %s.' % (quando[0].upper() + quando[1:], preco), prox2=conf[0].upper() + conf[1:] + '.',
                       prox_t=int(t_n), prox_p=ult if conc >= 4 else min(q for _e, q in serie[-3:]), prox_c=conc, prox_pat=pat,
                       prox_curto='%s · %s' % (mes, brl(ult) if conc >= 4 else '%s–%s' % (brl(min(ult6[-3:])), brl(max(ult6[-3:])))))
        elif serie:
            e, q = serie[-1]
            out.update(prox1='Sem previsão segura: só 1 promoção desde %s (%s, -%d%%, em %s).' % (out['desde'], brl(q), e[2], mm(e[0])))
        else:
            out.update(prox1='Sem previsão: nenhuma promoção anterior nas suas lojas desde %s.' % out['desde'])
        return out
