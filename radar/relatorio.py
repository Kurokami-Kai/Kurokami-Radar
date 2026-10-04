"""Pagina local com os alertas atuais (ponte ate o painel da etapa 3). Abre no navegador."""
import html
import json
from datetime import datetime

from . import caminhos

CSS = """
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;background:#1b2838;color:#c7d5e0;font:13px Arial,Helvetica,sans-serif}
header{background:#171a21;padding:16px 24px}header h1{margin:0;color:#fff;font-size:19px;letter-spacing:.05em}
header p{margin:4px 0 0;color:#8f98a0;font-size:12px}
main{max-width:1000px;margin:0 auto;padding:16px}
.row{display:grid;grid-template-columns:184px 1fr auto;gap:14px;align-items:center;background:rgba(0,0,0,.2);
 padding:6px 10px 6px 6px;margin-bottom:2px;color:inherit;text-decoration:none}
.row:hover{background:linear-gradient(90deg,rgba(103,193,245,.17),rgba(0,0,0,.2))}
.row img{width:184px;height:86px;object-fit:cover;display:block;background:#0b141e}
.n{color:#fff;font-size:15px}.m{color:#8f98a0;font-size:12px;margin-top:4px}.m b{color:#66c0f4;font-weight:400}
.pb{display:flex;height:34px}.pct{background:#4c6b22;color:#beee11;font-size:18px;padding:0 8px;display:flex;align-items:center}
.prs{background:#344654;color:#beee11;padding:0 9px;display:flex;align-items:center;font-size:14px;min-width:90px;justify-content:flex-end}
.foot{color:#56707f;font-size:11px;text-align:center;padding:20px}
@media(max-width:640px){.row{grid-template-columns:110px 1fr}.row img{width:110px;height:52px}.pb{grid-column:2}}
"""


def gerar(alertas, capas, novos_ids=()):
    def linha(a):
        url = a.get("url") or "https://store.steampowered.com/app/%d/" % a["appid"]
        img = capas.get(a["appid"]) or ""
        preco = "Grátis" if a["preco"] == 0 else "R$ %s" % ("%.2f" % (a["preco"] / 100)).replace(".", ",")
        from .analise import texto_outras
        outras = (" · " + texto_outras(a)) if a.get("outras") else ""
        novo = " · <b>novo</b>" if a["appid"] in novos_ids else ""
        return ('<a class="row" href="%s" target="_blank" rel="noopener"><img src="%s" alt="" loading="lazy" onerror="this.style.visibility=\'hidden\'">'
                '<div><div class="n">%s</div><div class="m">%s na %s%s%s</div></div>'
                '<div class="pb">%s<span class="prs">%s</span></div></a>') % (
            html.escape(url), html.escape(img), html.escape(a["nome"]), html.escape(a["motivo"]),
            html.escape(a["loja"]), html.escape(outras), novo,
            ('<span class="pct">-%d%%</span>' % a["corte"]) if a.get("corte") else "", preco)

    corpo = "".join(linha(a) for a in alertas) or '<p style="padding:30px;text-align:center;color:#8f98a0">Nada valendo a pena com os seus filtros agora.</p>'
    pag = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>Kurokami Radar - alertas</title><style>%s</style></head><body><header><h1>KUROKAMI RADAR</h1>'
           '<p>%d jogos valendo a pena com os seus filtros · atualizado %s</p></header><main>%s</main>'
           '<div class="foot">Preços via IsThereAnyDeal, GG.deals e Steam</div></body></html>') % (
        CSS, len(alertas), datetime.now().strftime("%d/%m %H:%M"), corpo)
    caminhos.garantir()
    with open(caminhos.ARQ_RELATORIO, "w", encoding="utf-8") as f:
        f.write(pag)
    return caminhos.ARQ_RELATORIO
