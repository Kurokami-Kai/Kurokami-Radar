"""Regenera docs/referencia.md a partir das assinaturas e docstrings do codigo."""
import ast
import glob
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = ["# Referência de módulos e funções", "",
       "Gerado a partir do código (assinatura + primeira parte da docstring). Para regenerar: `py tools/gerar_referencia.py`.", ""]
for f in ["radar.py"] + sorted(glob.glob("radar/*.py")):
    t = ast.parse(open(f, encoding="utf-8").read())
    doc = (ast.get_docstring(t) or "").strip().split("\n")[0]
    out += ["## `%s`" % f.replace("\\", "/")] + ([doc] if doc else []) + [""]
    for n in t.body:
        if isinstance(n, ast.ClassDef):
            out.append("- **class `%s`** — %s" % (n.name, (ast.get_docstring(n) or "").split("\n")[0]))
            for m in n.body:
                if isinstance(m, ast.FunctionDef) and not m.name.startswith("__"):
                    d = (ast.get_docstring(m) or "").split("\n")[0]
                    out.append("  - `%s(%s)`%s" % (m.name, ", ".join(a.arg for a in m.args.args if a.arg != "self"),
                                                   " — " + d if d else ""))
        elif isinstance(n, ast.FunctionDef):
            d = (ast.get_docstring(n) or "").split("\n")[0]
            out.append("- `%s(%s)`%s" % (n.name, ", ".join(a.arg for a in n.args.args), " — " + d if d else ""))
    out.append("")
open("docs/referencia.md", "w", encoding="utf-8").write("\n".join(out))
print("docs/referencia.md atualizado")
