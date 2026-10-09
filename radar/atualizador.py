"""Atualizacao pelo GitHub Releases: verifica, baixa o instalador novo e instala por cima (dados ficam).
So funciona no Hunter instalado (.exe); pelo codigo, avisa e mostra o link."""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

from . import VERSAO, caminhos, config

UA = {"User-Agent": "KurokamiRadar/%s" % VERSAO, "Accept": "application/vnd.github+json"}


def _v(t):
    return tuple(int(x) for x in re.findall(r"\d+", t or "")[:3]) or (0,)


def repo():
    return ((config.carregar().get("atualizacao") or {}).get("repo") or "").strip().strip("/")


def verificar():
    """{"atual","nova","tem_nova","url_exe","pagina","notas"} ou {"erro": ...}"""
    r_ = repo()
    if not r_:
        return {"erro": "repositorio de atualizacao nao configurado"}
    try:
        req = urllib.request.Request("https://api.github.com/repos/%s/releases/latest" % r_, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = {404: "nenhum release publicado ainda", 403: "o GitHub limitou as consultas por agora; tento de novo mais tarde"}.get(
            e.code, "GitHub respondeu HTTP %d" % e.code)
        if e.code == 404:
            msg += " (ou o repositório é privado: a verificação só funciona em repositório público)"
        return {"erro": msg, "pagina": "https://github.com/%s/releases" % r_}
    except Exception as e:
        return {"erro": "sem conexão com o GitHub (%s)" % e, "pagina": "https://github.com/%s/releases" % r_}
    tag = d.get("tag_name") or ""
    exe = next((a.get("browser_download_url") for a in d.get("assets") or []
                if (a.get("name") or "").lower().endswith(".exe")), None)
    return {"atual": VERSAO, "nova": tag.lstrip("vV"), "tem_nova": _v(tag) > _v(VERSAO) and bool(exe),
            "url_exe": exe, "pagina": d.get("html_url") or "https://github.com/%s/releases" % r_,
            "notas": (d.get("body") or "").strip()[:1500]}


def baixar(url, progresso=None):
    destino = os.path.join(tempfile.gettempdir(), "KurokamiRadar_Setup_novo.exe")
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r, open(destino, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        feito = 0
        while True:
            bloco = r.read(256 * 1024)
            if not bloco:
                break
            f.write(bloco)
            feito += len(bloco)
            if progresso:
                progresso(feito, total)
    return destino


def instalar(instalador):
    """Roda o instalador em silencio, separado deste processo; ele fecha o Hunter, instala e abre a versao nova."""
    subprocess.Popen([instalador, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     creationflags=0x00000008 | 0x00000200 if os.name == "nt" else 0,  # DETACHED | NEW_GROUP
                     close_fds=True)


def abrir_janela_separada():
    """Abre a janela de atualizacao num processo proprio (a bandeja ocupa a thread principal)."""
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "atualizar-app"]
    else:
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        cmd = [pyw if os.path.isfile(pyw) else sys.executable, os.path.join(caminhos.BASE, "radar.py"), "atualizar-app"]
    subprocess.Popen(cmd, cwd=caminhos.BASE)


def janela():
    """Kurokami Hunter (Atualizar): mostra as versoes e atualiza com um clique."""
    import threading
    import tkinter as tk
    import webbrowser
    from tkinter import ttk

    AZUL, FUNDO, TEXTO, FRACO = "#66c0f4", "#050505", "#d2d2d2", "#979797"
    raiz = tk.Tk()
    raiz.title("Kurokami Hunter - atualização")
    raiz.configure(bg=FUNDO)
    raiz.resizable(False, False)
    raiz.attributes("-topmost", True)
    raiz.after(600, lambda: raiz.attributes("-topmost", False))
    est = ttk.Style(raiz)
    try:
        est.theme_use("clam")
    except tk.TclError:
        pass
    est.configure("K.TButton", background="#1f1f1f", foreground="white", borderwidth=0, padding=(12, 6))
    est.map("K.TButton", background=[("active", AZUL)])
    est.configure("K.Horizontal.TProgressbar", troughcolor="#000000", background="#75b022", borderwidth=0)

    tk.Label(raiz, text="Kurokami Hunter", bg=FUNDO, fg="white", font=("Segoe UI", 15)).pack(anchor="w", padx=20, pady=(16, 0))
    st = tk.Label(raiz, text="Procurando versão nova…", bg=FUNDO, fg=TEXTO, font=("Segoe UI", 10), justify="left", wraplength=440)
    st.pack(anchor="w", padx=20, pady=(6, 4))
    notas = tk.Label(raiz, text="", bg=FUNDO, fg=FRACO, font=("Segoe UI", 9), justify="left", wraplength=440)
    notas.pack(anchor="w", padx=20)
    barra = ttk.Progressbar(raiz, style="K.Horizontal.TProgressbar", length=440, mode="determinate")
    botoes = tk.Frame(raiz, bg=FUNDO)
    botoes.pack(anchor="e", padx=20, pady=(12, 16))
    info = {}

    def atualizar():
        b_ok.config(state="disabled")
        barra.pack(padx=20, pady=(8, 0), before=botoes)
        st.config(text="Baixando a versão %s…" % info["nova"])

        def trabalho():
            try:
                arq = baixar(info["url_exe"], lambda f, t: raiz.after(0, lambda: barra.config(value=100 * f / t if t else 0)))
                raiz.after(0, lambda: st.config(text="Instalando… o Hunter fecha e abre de novo sozinho em alguns segundos."))
                instalar(arq)
                raiz.after(2500, raiz.destroy)
            except Exception as e:
                raiz.after(0, lambda: (st.config(text="Não deu para baixar: %s" % e, fg="#ef6f6a"), b_ok.config(state="normal")))
        threading.Thread(target=trabalho, daemon=True).start()

    b_ok = ttk.Button(botoes, text="Atualizar agora", style="K.TButton", command=atualizar)
    b_pag = ttk.Button(botoes, text="Abrir página", style="K.TButton", command=lambda: webbrowser.open(info.get("pagina", "")))
    ttk.Button(botoes, text="Fechar", style="K.TButton", command=raiz.destroy).pack(side="right", padx=4)

    def mostrar(d):
        info.update(d)
        if d.get("erro"):
            st.config(text="Não consegui verificar: %s." % d["erro"], fg="#e2a635")
            if d.get("pagina"):
                b_pag.pack(side="right", padx=4)
            return
        if not d["tem_nova"]:
            st.config(text="Você já está na versão mais nova (%s)." % d["atual"], fg="#a1cd44")
            return
        st.config(text="Versão nova disponível: %s (você tem a %s)." % (d["nova"], d["atual"]), fg="white")
        if d.get("notas"):
            notas.config(text=d["notas"][:600])
        b_pag.pack(side="right", padx=4)
        if getattr(sys, "frozen", False):
            b_ok.pack(side="right", padx=4)
        else:
            notas.config(text=(notas.cget("text") + "\n\n" if notas.cget("text") else "") +
                         "Você está rodando pelo código: atualize pelo .bat ou pelo repositório.")

    threading.Thread(target=lambda: (lambda d: raiz.after(0, lambda: mostrar(d)))(verificar()), daemon=True).start()
    raiz.mainloop()
