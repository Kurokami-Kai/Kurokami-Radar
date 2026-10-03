"""Mapa de um arquivo com numeros de linha, para ler SO o trecho necessario (economiza contexto).
Uso:
  py tools/mapa.py radar/painel.html          secoes de CSS/HTML/JS e funcoes JS
  py tools/mapa.py radar/coleta.py            classes e funcoes Python
  py tools/mapa.py radar/painel.html carrinho filtra pelo termo (secao, funcao ou id)
Depois leia so o intervalo: ex. linhas 957-1031."""
import ast
import re
import sys


def mapa_py(caminho, txt):
    t = ast.parse(txt)
    for n in t.body:
        if isinstance(n, ast.ClassDef):
            yield n.lineno, getattr(n, "end_lineno", n.lineno), "class %s" % n.name
            for m in n.body:
                if isinstance(m, ast.FunctionDef):
                    yield m.lineno, getattr(m, "end_lineno", m.lineno), "  def %s" % m.name
        elif isinstance(n, ast.FunctionDef):
            yield n.lineno, getattr(n, "end_lineno", n.lineno), "def %s" % n.name
        elif isinstance(n, ast.Assign) and all(isinstance(x, ast.Name) and x.id.isupper() for x in n.targets):
            yield n.lineno, getattr(n, "end_lineno", n.lineno), "%s =" % n.targets[0].id


def mapa_html(caminho, txt):
    linhas = txt.split("\n")
    for i, l in enumerate(linhas, 1):
        s = l.strip()
        m = re.match(r"/\* =+ (.+?) =+ \*/", s) or re.match(r"/\* -+ (.+?) -+ \*/", s)
        if m:
            yield i, None, "== %s" % m.group(1)
            continue
        m = re.match(r"<(section|aside|header|main|div) id=\"([\w-]+)\"", s)
        if m:
            yield i, None, "  <%s #%s>" % (m.group(1), m.group(2))
            continue
        m = re.match(r"(?:async\s+)?function\s+(\w+)\s*\(", s) or re.match(r"(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(?[\w,\s]*\)?\s*=>", s)
        if m:
            yield i, None, "  fn %s" % m.group(1)
            continue
        if s in ("<style>", "</style>", "<script>", "</script>") or s.startswith("<style>") or s.startswith("<script>"):
            yield i, None, s[:20]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    caminho, termo = sys.argv[1], (sys.argv[2].lower() if len(sys.argv) > 2 else None)
    txt = open(caminho, encoding="utf-8").read()
    total = txt.count("\n") + 1
    itens = list(mapa_py(caminho, txt) if caminho.endswith(".py") else mapa_html(caminho, txt))
    print("%s (%d linhas)" % (caminho, total))
    for k, (ini, fim, nome) in enumerate(itens):
        if fim is None:
            secao = nome.startswith("==")
            prox = next((it[0] for it in itens[k + 1:] if (it[2].startswith("==") if secao else True)), None)
            fim = (prox - 1) if prox else total
        if termo and termo not in nome.lower():
            continue
        print("%5d-%-5d %s" % (ini, fim, nome))


if __name__ == "__main__":
    main()
