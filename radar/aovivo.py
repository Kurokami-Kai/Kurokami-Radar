"""Jogo rodando agora, em tempo real, para as metas de jogar (radar/metas.py).
A Steam grava no registro do Windows o jogo em execucao (`HKCU\\Software\\Valve\\Steam\\RunningAppID`, 0 = nenhum): ler isso nao usa
rede. A cada `INTERVALO` s o Hunter soma o tempo do jogo que esta rodando em `ao_vivo` (segundos ainda NAO confirmados pela Steam).
Quando a leitura da biblioteca traz as horas novas do jogo (`Banco.salvar_tempo_jogo`), o confirmado vai para `horas_dia` e
sai de `ao_vivo`: nada conta em dobro. O que a Steam nunca confirma (modo offline sem voltar, jogo fora da conta) some em 3 dias.
So funciona com o Hunter aberto (bandeja); fora disso o tempo continua vindo so da Steam. Atalhos de jogos de fora da Steam
vem com ids enormes e sao ignorados."""
import threading
import time
from datetime import datetime, timedelta, timezone

INTERVALO = 30


def lendo():
    """O appid do jogo da Steam rodando agora, ou 0."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            v = int(winreg.QueryValueEx(k, "RunningAppID")[0])
    except (ImportError, OSError, ValueError, TypeError):
        return 0
    return v if 0 < v < 2 ** 31 else 0


def somar(b, appid, seg):
    b.con.execute("INSERT INTO ao_vivo VALUES(?,?,?) ON CONFLICT(appid) DO UPDATE SET seg=seg+excluded.seg, quando=excluded.quando",
                  (appid, int(seg), datetime.now(timezone.utc).replace(microsecond=0).isoformat()))


def limpar(b):
    """Apaga o que zerou e o que a Steam nao confirmou em 3 dias."""
    corte = (datetime.now(timezone.utc) - timedelta(days=3)).replace(microsecond=0).isoformat()
    b.con.execute("DELETE FROM ao_vivo WHERE seg<=0 OR quando<?", (corte,))


class AoVivo(threading.Thread):
    def __init__(self, servico):
        super().__init__(daemon=True)
        self.s = servico
        self.b = None

    def run(self):
        from . import config, metas
        from .banco import Banco
        antes, t0, falhas = 0, 0.0, 0
        while not self.s.parar:
            time.sleep(INTERVALO)
            try:
                a = lendo()
                agora = time.monotonic()
                if a:
                    if self.b is None:
                        self.b = Banco()
                    # sessao em andamento: o tempo desde o ultimo toque (limitado, o PC pode ter dormido); 1o toque: meio intervalo
                    seg = min(agora - t0, INTERVALO * 3) if a == antes and t0 else INTERVALO // 2
                    if self.b.um("SELECT 1 FROM jogo WHERE appid=?", a):
                        somar(self.b, a, seg)
                        self.b.commit()
                        cfg = config.carregar()
                        if (cfg.get("metas") or {}).get("horas_dia") or (cfg.get("metas") or {}).get("terminar_qtd"):
                            metas.avaliar(self.b, cfg, self.s.log)
                elif antes and self.b is not None:
                    limpar(self.b)
                    self.b.commit()
                antes, t0, falhas = a, agora, 0
            except Exception as e:   # banco ocupado ou fechado: tenta de novo no proximo toque
                falhas += 1
                if falhas == 1 or falhas % 20 == 0:
                    self.s.log("Jogo em tempo real: %s" % e)
                try:
                    if self.b is not None:
                        self.b.con.close()
                except Exception:
                    pass
                self.b = None
