"""Notificacoes nativas do Windows (central de notificacoes), sem dependencias.
Registra o app no Windows (HKCU, sem admin) para aparecer com nome e icone proprios."""
import base64
import os
import subprocess
import sys
import urllib.request
from xml.sax.saxutils import escape, quoteattr

from . import caminhos

APP_ID = "Kurokami.Radar"
CAPAS = os.path.join(caminhos.DADOS, "capas")


def registrar_app(icone=None):
    if os.name != "nt":
        return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\AppUserModelId\%s" % APP_ID) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Kurokami Hunter")
        if icone and os.path.isfile(icone):
            winreg.SetValueEx(k, "IconUri", 0, winreg.REG_SZ, icone)
        winreg.SetValueEx(k, "IconBackgroundColor", 0, winreg.REG_SZ, "FF050505")


def capa(appid, url):
    """Baixa a capa do jogo uma vez (vira a imagem grande da notificacao)."""
    if not url:
        return None
    os.makedirs(CAPAS, exist_ok=True)
    arq = os.path.join(CAPAS, "%s.jpg" % appid)
    if not os.path.isfile(arq):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KurokamiRadar"})
            with urllib.request.urlopen(req, timeout=20) as r, open(arq, "wb") as f:
                f.write(r.read())
        except Exception:
            return None
    return arq


def _uri(caminho):
    return "file:///" + os.path.abspath(caminho).replace("\\", "/")


def mostrar(titulo, texto, clique=None, botoes=(), imagem=None, rodape=None, silenciosa=False):
    """botoes: [(rotulo, url)]. url pode ser http(s) ou file:///."""
    if os.name != "nt":
        print("[notificacao] %s | %s" % (titulo, texto))
        return True
    linhas = ['<toast activationType="protocol"%s>' % (" launch=%s" % quoteattr(clique) if clique else ""),
              '<visual><binding template="ToastGeneric">']
    if imagem:
        linhas.append('<image placement="hero" src=%s/>' % quoteattr(_uri(imagem)))
    linhas.append("<text>%s</text>" % escape(titulo))
    for t in str(texto).split("\n"):
        linhas.append("<text>%s</text>" % escape(t))
    if rodape:
        linhas.append('<text placement="attribution">%s</text>' % escape(rodape))
    linhas.append("</binding></visual>")
    if botoes:
        linhas.append("<actions>")
        for rot, url in list(botoes)[:5]:
            linhas.append('<action activationType="protocol" content=%s arguments=%s/>' % (quoteattr(rot), quoteattr(url)))
        linhas.append("</actions>")
    if silenciosa:
        linhas.append('<audio silent="true"/>')
    linhas.append("</toast>")
    xml = "".join(linhas)
    # here-string com aspas simples: o PowerShell nao interpreta nada dentro (nem o $ de "R$")
    script = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null\n"
              "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] > $null\n"
              "$x = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
              "$x.LoadXml(@'\n%s\n'@)\n"
              "$t = [Windows.UI.Notifications.ToastNotification]::new($x)\n"
              "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('%s').Show($t)\n") % (xml, APP_ID)
    cod = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                          "-ExecutionPolicy", "Bypass", "-EncodedCommand", cod],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x08000000)  # CREATE_NO_WINDOW
        return True
    except Exception as e:
        print("Falha ao notificar: %s" % e, file=sys.stderr)
        return False
