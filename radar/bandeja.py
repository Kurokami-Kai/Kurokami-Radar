"""Icone na bandeja do Windows. Roda o servico em segundo plano."""
import os
import socket
import subprocess
import sys

from . import caminhos, credenciais, notificar
from .banco import Banco
from .servico import Servico, criar_log

PORTA_TRAVA = 47811  # impede duas copias rodando ao mesmo tempo


VERMELHO = (225, 29, 46)


def desenhar_icone(cor_ponto=(255, 42, 61), tam=64):
    """Mira preta e vermelha do Kurokami Hunter (o mesmo desenho do logo do painel). Desenha em 4x e reduz (bordas lisas)."""
    from PIL import Image, ImageDraw
    k = max(4, -(-tam * 2 // 64))
    im = Image.new("RGBA", (64 * k, 64 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2 * k, 2 * k, 62 * k, 62 * k), fill=(11, 11, 11, 255), outline=VERMELHO + (255,), width=4 * k)
    d.ellipse((16 * k, 16 * k, 48 * k, 48 * k), outline=(138, 18, 32, 255), width=3 * k)
    for x0, y0, x1, y1 in ((32, 8, 32, 19), (32, 45, 32, 56), (8, 32, 19, 32), (45, 32, 56, 32)):
        d.line((x0 * k, y0 * k, x1 * k, y1 * k), fill=VERMELHO + (255,), width=5 * k)
    d.ellipse((26 * k, 26 * k, 38 * k, 38 * k), fill=cor_ponto + (255,))
    return im.resize((tam, tam), Image.LANCZOS)


def abrir(caminho):
    if os.name == "nt":
        os.startfile(caminho)
    else:
        subprocess.Popen(["xdg-open", caminho])


def abrir_log():
    """Abre o log; se ainda nao existe (nada foi registrado), cria vazio antes."""
    if not os.path.isfile(caminhos.ARQ_LOG):
        caminhos.garantir()
        open(caminhos.ARQ_LOG, "a", encoding="utf-8").close()
    abrir(caminhos.ARQ_LOG)


def _comando_atual():
    if getattr(sys, "frozen", False):
        return [sys.executable, "bandeja", "--esperar"]
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return [pyw if os.path.isfile(pyw) else sys.executable, os.path.join(caminhos.BASE, "radar.py"), "bandeja", "--esperar"]


def main(esperar=False, abrir_painel=False):
    import time
    trava = socket.socket()
    fim = time.time() + (20 if esperar else 0)
    while True:
        try:
            trava.bind(("127.0.0.1", PORTA_TRAVA))
            break
        except OSError:
            if time.time() < fim:
                time.sleep(0.5)
                continue
            notificar.mostrar("Kurokami Hunter", "Já está rodando: procure o ícone na bandeja, perto do relógio.\n"
                              "Depois de atualizar, use \"Reiniciar\" no menu dele.")
            return
    import pystray

    log = criar_log()
    caminhos.garantir()
    icone = desenhar_icone()
    icone.save(caminhos.ARQ_ICONE)
    try:
        notificar.registrar_app(caminhos.ARQ_ICONE)
    except Exception as e:
        log("Nao registrei o app no Windows (%s)" % e)

    from . import config as _cfg
    if credenciais.faltando_obrigatorias() or not (_cfg.carregar().get("perfil_steam") or "").strip():
        try:
            from . import janela_chaves
            janela_chaves.abrir()
        except Exception as e:
            log("Janela de chaves falhou: %s" % e)

    tray = None

    def pausado():
        b = Banco()
        v = bool(b.meta("pausado"))
        b.con.close()
        return v

    def alternar_pausa(_i, _item):
        b = Banco()
        b.meta("pausado", not b.meta("pausado"))
        b.commit()
        b.con.close()
        atualizar_titulo()

    def atualizar_titulo():
        if not tray:
            return
        if serv.estado == "verificando":
            from . import progresso
            pr = progresso.foto()
            pct = (" %d%%" % (100 * pr["atual"] / pr["total"])) if pr.get("total") else ""
            txt = "verificando (%s): %s%s" % ("completa" if pr.get("modo") == "completa" else "rápida",
                                             (pr.get("etapa") or "")[:60], pct)
        else:
            txt = "próxima checagem %s" % serv.proxima.strftime("%H:%M")
            if serv.ultimo:
                txt = "%d valendo a pena · %s" % (serv.ultimo[1], txt)
            if serv.estado == "erro":
                txt = "erro na última checagem · " + txt
        tray.title = ("Kurokami Hunter%s\n%s" % (" (pausado)" if pausado() else "", txt))[:127]
        tray.icon = desenhar_icone((226, 166, 53) if serv.estado == "erro" else
                                   (143, 152, 160) if pausado() else (255, 42, 61))

    serv = Servico(log, ao_mudar=atualizar_titulo)
    from . import painel
    painel.CONTROLE["servico"] = serv
    painel.CONTROLE["ao_sair"] = lambda: sair(None, None)
    try:
        painel.iniciar()
    except OSError as e:
        log("Painel nao iniciou (porta %d ocupada?): %s" % (painel.PORTA, e))
    ir_ao_painel = lambda *_: __import__("webbrowser").open(painel.url())
    if abrir_painel:
        ir_ao_painel()

    def sair(_i, _item):
        serv.parar = True
        serv.acordar.set()
        tray.stop()

    def reiniciar(_i, _item):
        """Abre uma copia nova (que espera esta fechar) e sai. Use depois de atualizar os arquivos."""
        log("Reiniciando a pedido do usuario")
        subprocess.Popen(_comando_atual(), cwd=caminhos.BASE, creationflags=0x08000000 if os.name == "nt" else 0)
        trava.close()
        try:
            painel.CONTROLE["srv"].shutdown()
            painel.CONTROLE["srv"].server_close()
        except Exception:
            pass
        sair(_i, _item)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir painel", ir_ao_painel, default=True),
        pystray.MenuItem("Verificar agora", lambda *_: serv.agora()),
        pystray.MenuItem("Pausar notificações", alternar_pausa, checked=lambda _i: pausado()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Chaves e perfil…", lambda *_: subprocess.Popen([sys.executable] + (
            [] if getattr(sys, "frozen", False) else [os.path.join(caminhos.BASE, "radar.py")]) + ["chaves"])),
        pystray.MenuItem("Abrir pasta dos dados", lambda *_: abrir(caminhos.RAIZ_DADOS)),
        pystray.MenuItem("Ver log", lambda *_: abrir_log()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Procurar atualização…", lambda *_: __import__("radar.atualizador", fromlist=["x"]).abrir_janela_separada()),
        pystray.MenuItem("Reiniciar", reiniciar),
        pystray.MenuItem("Sair", sair),
    )
    tray = pystray.Icon("KurokamiRadar", icone, "Kurokami Hunter", menu)
    def checar_versao():
        import time
        from . import atualizador, config as cfgm
        while not serv.parar:
            if (cfgm.carregar().get("atualizacao") or {}).get("verificar", True):
                d = atualizador.verificar()
                painel.CONTROLE["atualizacao"] = d
                if d.get("tem_nova") and painel.CONTROLE.get("avisado") != d["nova"]:
                    painel.CONTROLE["avisado"] = d["nova"]
                    notificar.mostrar("Kurokami Hunter %s disponível" % d["nova"],
                                      "Você tem a %s. Clique para atualizar (seus dados ficam)." % d["atual"],
                                      clique=painel.url() + "/acao?atualizar=1",
                                      botoes=[("Atualizar agora", painel.url() + "/acao?atualizar=1"), ("Ver novidades", d["pagina"])])
                    log("Versao nova disponivel: %s" % d["nova"])
            for _ in range(24 * 60):  # de novo daqui a 1 dia (o Hunter costuma ficar aberto)
                if serv.parar:
                    return
                time.sleep(60)

    def tooltip_vivo():
        import time
        while not serv.parar:
            if serv.estado == "verificando":
                try:
                    atualizar_titulo()
                except Exception:
                    pass
            time.sleep(3)

    log("Bandeja iniciada")
    serv.start()
    __import__("threading").Thread(target=tooltip_vivo, daemon=True).start()
    __import__("threading").Thread(target=checar_versao, daemon=True).start()
    tray.run(setup=lambda t: (setattr(t, "visible", True), atualizar_titulo()))
    log("Bandeja encerrada")
