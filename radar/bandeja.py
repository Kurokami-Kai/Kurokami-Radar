"""Icone na bandeja do Windows. Roda o servico em segundo plano."""
import os
import socket
import subprocess
import sys

from . import caminhos, credenciais, notificar
from .banco import Banco
from .servico import Servico, criar_log

PORTA_TRAVA = 47811  # impede duas copias rodando ao mesmo tempo


def desenhar_icone(cor_ponto=(102, 192, 244)):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 62, 62), fill=(23, 26, 33, 255), outline=(199, 213, 224, 255), width=3)
    for r, a in ((22, 170), (14, 210)):
        d.arc((32 - r, 32 - r, 32 + r, 32 + r), 200, 340, fill=(102, 192, 244, a), width=3)
    d.line((32, 32, 50, 16), fill=(199, 213, 224, 255), width=3)
    d.ellipse((26, 26, 38, 38), fill=cor_ponto + (255,))
    return im


def abrir(caminho):
    if os.name == "nt":
        os.startfile(caminho)
    else:
        subprocess.Popen(["xdg-open", caminho])


def _comando_atual():
    if getattr(sys, "frozen", False):
        return [sys.executable, "bandeja", "--esperar"]
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return [pyw if os.path.isfile(pyw) else sys.executable, os.path.join(caminhos.BASE, "radar.py"), "bandeja", "--esperar"]


def main(esperar=False, abrir=False):
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
            notificar.mostrar("Kurokami Radar", "Já está rodando: procure o ícone na bandeja, perto do relógio.\n"
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
            txt = "verificando agora…"
        else:
            txt = "próxima checagem %s" % serv.proxima.strftime("%H:%M")
            if serv.ultimo:
                txt = "%d no menor histórico · %s" % (serv.ultimo[1], txt)
            if serv.estado == "erro":
                txt = "erro na última checagem · " + txt
        tray.title = ("Kurokami Radar%s\n%s" % (" (pausado)" if pausado() else "", txt))[:127]
        tray.icon = desenhar_icone((226, 166, 53) if serv.estado == "erro" else
                                   (143, 152, 160) if pausado() else (102, 192, 244))

    serv = Servico(log, ao_mudar=atualizar_titulo)
    from . import painel
    painel.CONTROLE["servico"] = serv
    painel.CONTROLE["ao_sair"] = lambda: sair(None, None)
    try:
        painel.iniciar()
    except OSError as e:
        log("Painel nao iniciou (porta %d ocupada?): %s" % (painel.PORTA, e))
    abrir_painel = lambda *_: __import__("webbrowser").open(painel.url())
    if abrir:
        abrir_painel()

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
        pystray.MenuItem("Abrir painel", abrir_painel, default=True),
        pystray.MenuItem("Verificar agora", lambda *_: serv.agora()),
        pystray.MenuItem("Pausar notificações", alternar_pausa, checked=lambda _i: pausado()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Chaves e perfil…", lambda *_: subprocess.Popen([sys.executable] + (
            [] if getattr(sys, "frozen", False) else [os.path.join(caminhos.BASE, "radar.py")]) + ["chaves"])),
        pystray.MenuItem("Abrir pasta dos dados", lambda *_: abrir(caminhos.RAIZ_DADOS)),
        pystray.MenuItem("Ver log", lambda *_: abrir(caminhos.ARQ_LOG)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Reiniciar (depois de atualizar)", reiniciar),
        pystray.MenuItem("Sair", sair),
    )
    tray = pystray.Icon("KurokamiRadar", icone, "Kurokami Radar", menu)
    log("Bandeja iniciada")
    serv.start()
    tray.run(setup=lambda t: (setattr(t, "visible", True), atualizar_titulo()))
    log("Bandeja encerrada")
