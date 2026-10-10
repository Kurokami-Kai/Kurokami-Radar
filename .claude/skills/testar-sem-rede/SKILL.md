---
name: testar-sem-rede
description: Testa API do painel, avaliação, raridade, carrinho, biblioteca e visual com cópia de banco real, sem chamar Steam/ITAD/GG.deals. Use depois de alterar painel.py, painel.html, analise.py ou banco.py, e ao reproduzir bugs.
---

# Testar sem rede

1. Copie o banco real para uma pasta de teste (nunca teste no banco do usuário): `dados/radar.sqlite3` (pelo código) ou `%LOCALAPPDATA%\Kurokami Radar\dados\radar.sqlite3` (instalado).
2. Com o código atual apontando para a cópia:
   ```python
   from radar import painel, analise, config
   from radar.banco import Banco
   painel.api_lista({}); painel.api_jogo({"appid": ["1659040"]}); painel.api_carrinho({}); painel.api_biblioteca({})
   b = Banco(); cfg = config.carregar()
   of = {a: [dict(o, drm_steam=True) for o in l] for a, l in b.ofertas_atuais().items()}
   al = analise.avaliar(analise.Contexto(b, cfg), of, {}, {"Steam", "Nuuvem", "GreenManGaming"})
   print(len(al), [(a["nome"], a["raridade"]) for a in al[:10]])
   ```
   Imprima contagens e amostras, não listas inteiras.
3. Visual: `py radar.py painel` → `http://127.0.0.1/kurokami`. Para prints e cliques automatizados, use a skill **`webapp-testing`** (anthropics/skills) apontando para essa URL; veja o console.
4. Diga o que **não** dá para testar assim (notificações, bandeja, carrinho direto na Steam, instalador, atualização) e peça o log ao usuário.
