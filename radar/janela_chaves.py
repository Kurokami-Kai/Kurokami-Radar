"""Janela de primeiro uso para as chaves. Campo de texto do Windows: Ctrl+V e o botao direito funcionam."""
import tkinter as tk
import webbrowser
from tkinter import ttk

from . import config, credenciais
from .validar import DICAS, testar, testar_perfil

AZUL, FUNDO, PAINEL, TEXTO, FRACO = "#66c0f4", "#1b2838", "#2a475e", "#c7d5e0", "#8f98a0"


def abrir():
    raiz = tk.Tk()
    raiz.title("Kurokami Radar - perfil e chaves")
    raiz.configure(bg=FUNDO)
    raiz.resizable(False, False)
    raiz.attributes("-topmost", True)
    raiz.after(600, lambda: raiz.attributes("-topmost", False))
    est = ttk.Style(raiz)
    try:
        est.theme_use("clam")
    except tk.TclError:
        pass
    est.configure("K.TButton", background=PAINEL, foreground="white", borderwidth=0, padding=(10, 5))
    est.map("K.TButton", background=[("active", AZUL)])

    tk.Label(raiz, text="Perfil e chaves de API", bg=FUNDO, fg="white", font=("Segoe UI", 15)).grid(
        row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(16, 2))
    tk.Label(raiz, text="Ficam guardadas no Gerenciador de Credenciais do Windows. Cole com Ctrl+V ou pelo botão direito.",
             bg=FUNDO, fg=FRACO, font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=4, sticky="w", padx=18, pady=(0, 12))

    campos = {}
    # ---- perfil Steam (fica no config.json; nao e segredo)
    tk.Label(raiz, text="Seu perfil Steam", bg=FUNDO, fg=TEXTO, font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", padx=18)
    lk = tk.Label(raiz, text="abrir meu perfil ↗", bg=FUNDO, fg=AZUL, cursor="hand2", font=("Segoe UI", 9, "underline"))
    lk.grid(row=2, column=1, sticky="w")
    lk.bind("<Button-1>", lambda e: webbrowser.open("https://steamcommunity.com/my/profile"))
    var_perfil = tk.StringVar(value=config.carregar().get("perfil_steam") or "")
    ent_p = tk.Entry(raiz, textvariable=var_perfil, width=52, bg="#0e141b", fg="white", insertbackground="white",
                     relief="flat", font=("Consolas", 10))
    ent_p.grid(row=3, column=0, columnspan=2, sticky="we", padx=(18, 6), pady=(2, 0), ipady=5)
    st_p = tk.Label(raiz, text="Cole o link do perfil (ex.: https://steamcommunity.com/id/seunome) ou o SteamID64.",
                    bg=FUNDO, fg=FRACO, font=("Segoe UI", 9), wraplength=520, justify="left")
    st_p.grid(row=4, column=0, columnspan=4, sticky="w", padx=18, pady=(2, 10))
    linha = 5
    for nome, (titulo, onde, obrig) in credenciais.CHAVES.items():
        tk.Label(raiz, text=titulo + ("" if obrig else "  (opcional)"), bg=FUNDO, fg=TEXTO,
                 font=("Segoe UI", 10, "bold")).grid(row=linha, column=0, sticky="w", padx=18)
        link = tk.Label(raiz, text="onde gerar ↗", bg=FUNDO, fg=AZUL, cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.grid(row=linha, column=1, sticky="w")
        url = "https://" + onde.split("https://")[-1].split(" ")[0]
        link.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        var = tk.StringVar(value=credenciais.ler(nome) or "")
        ent = tk.Entry(raiz, textvariable=var, show="•", width=52, bg="#0e141b", fg="white", insertbackground="white",
                       relief="flat", font=("Consolas", 10))
        ent.grid(row=linha + 1, column=0, columnspan=2, sticky="we", padx=(18, 6), pady=(2, 0), ipady=5)
        menu = tk.Menu(raiz, tearoff=0)
        def colar(e=ent):
            try:
                txt = raiz.clipboard_get()
            except tk.TclError:
                return
            e.delete(0, "end")
            e.insert(0, credenciais.limpar(txt))
        menu.add_command(label="Colar", command=colar)
        ent.bind("<Button-3>", lambda ev, m=menu: m.tk_popup(ev.x_root, ev.y_root))
        mostrar = tk.BooleanVar(value=False)
        tk.Checkbutton(raiz, text="mostrar", variable=mostrar, bg=FUNDO, fg=FRACO, selectcolor=FUNDO,
                       activebackground=FUNDO, command=lambda e=ent, m=mostrar: e.config(show="" if m.get() else "•")
                       ).grid(row=linha + 1, column=2, padx=4)
        st = tk.Label(raiz, text="", bg=FUNDO, fg=FRACO, font=("Segoe UI", 9), wraplength=520, justify="left")
        st.grid(row=linha + 2, column=0, columnspan=4, sticky="w", padx=18, pady=(2, 10))
        campos[nome] = (var, st)
        linha += 3

    def verificar(salvar):
        tudo_ok = True
        perfil = var_perfil.get().strip()
        st_p.config(text="testando o perfil…", fg=FRACO)
        raiz.update_idletasks()
        okp, msgp, _sid = testar_perfil(perfil)
        if okp:
            st_p.config(text="✓ " + msgp, fg="#a1cd44")
            if salvar:
                cfg = config.carregar()
                cfg["perfil_steam"] = perfil
                config.salvar(cfg)
        else:
            st_p.config(text="✗ " + msgp, fg="#ef6f6a")
            tudo_ok = False
        for nome, (var, st) in campos.items():
            v = credenciais.limpar(var.get())
            var.set(v)
            if not v:
                obrig = credenciais.CHAVES[nome][2]
                st.config(text="obrigatória" if obrig else ("sem chave: keyshops ficam de fora" if nome == "ggdeals" else
                          "sem chave: a biblioteca vem do userdata.json"), fg="#e2a635" if obrig else FRACO)
                tudo_ok &= not obrig
                if salvar:
                    credenciais.gravar(nome, None)
                continue
            st.config(text="testando…", fg=FRACO)
            raiz.update_idletasks()
            ok, msg = testar(nome, v)
            if ok:
                st.config(text="✓ funcionando (%d caracteres)" % len(v), fg="#a1cd44")
                if salvar:
                    credenciais.gravar(nome, v)
            elif "sem resposta" in msg:
                st.config(text="não deu para testar agora (%s). %s" % (msg, "Salva mesmo assim." if salvar else ""), fg="#e2a635")
                if salvar:
                    credenciais.gravar(nome, v)
            else:
                st.config(text="✗ %s\n%s" % (msg, DICAS[nome]), fg="#ef6f6a")
                tudo_ok = False
        if salvar and tudo_ok:
            raiz.after(900, raiz.destroy)
        return tudo_ok

    bar = tk.Frame(raiz, bg=FUNDO)
    bar.grid(row=linha, column=0, columnspan=4, sticky="e", padx=18, pady=(0, 16))
    ttk.Button(bar, text="Testar", style="K.TButton", command=lambda: verificar(False)).pack(side="left", padx=4)
    ttk.Button(bar, text="Salvar", style="K.TButton", command=lambda: verificar(True)).pack(side="left", padx=4)
    raiz.mainloop()
