#!/usr/bin/env python3
# odoo17_attrs_translate.py
import re, ast, sys
from pathlib import Path
from typing import Any

ATTRS_RE = re.compile(r'attrs\s*=\s*([\'"])(.*?)\1', re.DOTALL)

def _expr_from_tuple(cond: tuple) -> str:
    fld = cond[0]
    if len(cond) == 2:
        op, val = '=', cond[1]
    else:
        op, val = str(cond[1]).strip(), cond[2]
    if op == '=' and isinstance(val, (list, tuple)):
        op = 'in'
    op_map = {'=':'==','==':'==','!=':'!=','>':'>','<':'<','>=':'>=','<=':'<=','in':'in','not in':'not in'}
    pyop = op_map.get(op)
    if not pyop:
        raise ValueError(f"Operador no soportado: {op}")
    # Simplificaciones booleanas
    if pyop == '==':
        if val is True:  return f"({fld})"
        if val is False: return f"(not {fld})"
    if pyop == '!=':
        if val is True:  return f"(not {fld})"
        if val is False: return f"({fld})"
    return f"({fld} {pyop} {repr(val)})"

def _build_expr_prefix(tokens: list) -> str:
    it = iter(tokens)
    def consume() -> str:
        t: Any = next(it)
        if isinstance(t, list):
            return _build_expr_prefix(t)
        if isinstance(t, tuple):
            return _expr_from_tuple(t)
        if t == '&':
            a, b = consume(), consume()
            return f"({a} and {b})"
        if t == '|':
            a, b = consume(), consume()
            return f"({a} or {b})"
        if t == '!':
            a = consume()
            return f"(not ({a}))"
        return repr(t)
    return consume()

def _to_expr(value: Any) -> str:
    if isinstance(value, list):
        # Si hay operadores prefijo, parsea en notación polaca
        if any(isinstance(x, str) and x in ('&','|','!') for x in value):
            return _build_expr_prefix(value)
        # Si no, AND implícito
        return "(" + " and ".join(_to_expr(x) for x in value) + ")"
    if isinstance(value, tuple):
        return _expr_from_tuple(value)
    if value in ('&','|','!'):
        return "True"
    return repr(value)

def _repl(m: re.Match) -> str:
    raw = m.group(2).strip()
    try:
        d = ast.literal_eval(raw)
        if not isinstance(d, dict):
            return m.group(0)
        parts = []
        for k in ('invisible','readonly','required'):
            if k in d:
                parts.append(f'{k}="{_to_expr(d[k])}"')
        return (" " + " ".join(parts) + " ") if parts else ""
    except Exception:
        return m.group(0)

def process_file(p: Path) -> bool:
    s = p.read_text(encoding="utf-8", errors="ignore")
    new = re.sub(ATTRS_RE, _repl, s)
    if new != s:
        bak = p.with_suffix(p.suffix + ".bak")
        if not bak.exists():
            bak.write_text(s, encoding="utf-8")
        p.write_text(new, encoding="utf-8")
        return True
    return False

def main():
    if len(sys.argv) != 2:
        print("Uso: python odoo17_attrs_translate.py RUTA_ADDONS"); sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print("Ruta no encontrada"); sys.exit(1)
    xmls = list(root.rglob("*.xml"))
    changed = sum(process_file(p) for p in xmls)
    print(f"XML modificados: {changed}/{len(xmls)}")

if __name__ == "__main__":
    main()
