"""Inventory candidate tenant-scoped endpoints without importing product code.

Usage: python3 ops/robot-plans/inventory_tenant_endpoints.py
Writes Markdown to stdout. This is heuristic discovery, not an authorization audit.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {".git", ".venv", "venv", "node_modules", "__pycache__", "ops"}
KEYWORDS = ("company_id", "tenant_id", "platform_admin", "client_preview")
MAX_FILES = 3000


def discover():
    rows = []
    scanned = 0
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        scanned += 1
        if scanned > MAX_FILES:
            break
        try:
            source = path.read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = [ast.unparse(d) for d in node.decorator_list]
            routes = [d for d in decorators if any(
                token in d for token in (".get(", ".post(", ".put(", ".patch(", ".delete(", ".api_route(")
            )]
            if not routes:
                continue
            snippet = ast.get_source_segment(source, node) or ""
            hits = [word for word in KEYWORDS if word in snippet]
            if hits:
                rows.append((str(path.relative_to(ROOT)), node.lineno, node.name, ", ".join(routes), ", ".join(hits)))
    return scanned, rows


if __name__ == "__main__":
    count, matches = discover()
    print("# TALVOA — inventário de endpoints com indícios de contexto de tenant")
    print()
    print(f"Arquivos Python inspecionados: {count}. Rotas candidatas: {len(matches)}.")
    print()
    print("| Arquivo:linha | Função | Rota | Indícios |")
    print("|---|---|---|---|")
    for path, line, name, routes, hits in matches:
        print(f"| \`{path}:{line}\` | \`{name}\` | \`{routes.replace('|', ' ')}\` | {hits} |")
    print()
    print("Triagem estática: revisar autenticação, autorização e auditoria manualmente.")
