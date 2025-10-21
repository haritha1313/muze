import ast
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set
import requests
import textwrap

# ---- env ----
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")
BASE_SHA = os.getenv("BASE_SHA")
HEAD_SHA = os.getenv("HEAD_SHA")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")
DOCS_EXTRAS = [p.strip() for p in os.getenv("DOCS_EXTRAS", "README.md").split(",") if p.strip()]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

CODE_EXTS = {".py"}

# ---- git helpers ----
def run(cmd: List[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def diff_name_status(base: str, head: str) -> List[str]:
    out = run(["git", "diff", "--name-status", f"{base}...{head}"]).strip()
    return out.splitlines() if out else []

def list_changed_files() -> Dict[str, str]:
    """path -> status (A/M/D/...)"""
    files: Dict[str, str] = {}
    for line in diff_name_status(BASE_SHA, HEAD_SHA):
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]  # handles renames
        files[path] = status
    return files

# ---- code parsing ----
def is_code_file(p: str) -> bool:
    return Path(p).suffix in CODE_EXTS

def parse_functions_from_source(src: str) -> Set[str]:
    """Return function signatures like name(argcount)."""
    if not src:
        return set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    fns = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            if args and args[0] in {"self", "cls"}:
                args = args[1:]
            fns.add(f"{node.name}({len(args)})")
    return fns

def parse_top_level_names(src: str) -> Set[str]:
    if not src:
        return set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    names = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names

def extract_functions_py(file_path: str) -> List[str]:
    """Top-level function names in a .py file at HEAD."""
    try:
        src = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return []
    return sorted(parse_top_level_names(src))

# ---- docs scanning ----
def load_docs_at_head() -> Dict[str, str]:
    docs = {}
    for extra in DOCS_EXTRAS:
        p = Path(extra)
        if p.exists() and p.is_file():
            docs[str(p)] = p.read_text(encoding="utf-8", errors="ignore")
    d = Path(DOCS_DIR)
    if d.exists():
        for md in list(d.rglob("*.md")) + list(d.rglob("*.mdx")):
            try:
                docs[str(md)] = md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    return docs

def is_mentioned(name: str) -> bool:
    """Loose mention in docs (word boundary)."""
    docs_map = load_docs_at_head()
    pat = re.compile(rf"(^|\W){re.escape(name)}(\W|$)")
    for content in docs_map.values():
        if pat.search(content):
            return True
    return False

# ---- comment ----
def post_pr_comment(message: str):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    # hidden marker so update_docs.py can patch this same comment later
    marker = f"<!-- DOC-BOT:PR:{PR_NUMBER} -->"
    body = marker + "\n" + message
    resp = requests.post(url, headers=headers, json={"body": body})
    resp.raise_for_status()

# ---- analyze + format ----
def analyze() -> str:
    changed = list_changed_files()
    code_changed = [p for p in changed if is_code_file(p)]

    lines = []
    lines.append("## 📚 Code vs Docs Analysis")
    lines.append("")
    if not code_changed:
        lines.append("No tracked code file changes.")
        return "\n".join(lines)

    lines.append("**Code files changed:**")
    for p in code_changed:
        lines.append(f"- `{p}` ({changed[p]})")
    lines.append("")

    docs_map = load_docs_at_head()
    missing_total = 0

    for path in code_changed:
        head_src = Path(path).read_text(encoding="utf-8", errors="ignore") if Path(path).exists() else ""
        try:
            base_src = run(["git", "show", f"{BASE_SHA}:{path}"])
        except subprocess.CalledProcessError:
            base_src = ""

        base_sigs = parse_functions_from_source(base_src)
        head_sigs = parse_functions_from_source(head_src)

        added = sorted(head_sigs - base_sigs)
        removed = sorted(base_sigs - head_sigs)

        base_by_name = {s.split("(")[0]: s for s in base_sigs}
        head_by_name = {s.split("(")[0]: s for s in head_sigs}
        modified = []
        for nm in set(base_by_name) & set(head_by_name):
            if base_by_name[nm] != head_by_name[nm]:
                modified.append((base_by_name[nm], head_by_name[nm]))

        lines.append(f"### `{path}`")
        if added:
            lines.append("**Added functions**")
            for s in added:
                lines.append(f"- `{s}`")
        if modified:
            lines.append("**Signature changes**")
            for b, a in modified:
                lines.append(f"- `{b}` ➜ `{a}`")
        if removed:
            lines.append("**Removed functions**")
            for s in removed:
                lines.append(f"- `{s}`")

        # doc coverage for added/modified names
        to_check = sorted({*(n.split('(')[0] for n in added), *(n[1].split('(')[0] for n in modified)})
        missing = []
        for nm in to_check:
            if not any(re.search(rf"(^|\W){re.escape(nm)}(\W|$)", content) for content in docs_map.values()):
                missing.append(nm)

        if missing:
            missing_total += len(missing)
            for nm in missing:
                mod = Path(path).stem
                suggestion = f"{DOCS_DIR}/{mod}.md" if Path(f"{DOCS_DIR}/{mod}.md").exists() else "README.md"
                lines.append("**❌ Missing docs**")
                lines.append(f"- `{nm}` ➜ consider updating `{suggestion}`")
        if not any([added, modified, removed]):
            lines.append("_No function-level changes detected._")
        lines.append("")

    if missing_total == 0:
        lines.append("✅ All added/changed functions are referenced in docs.")
    else:
        lines.append(textwrap.dedent("""
        ---
        💡 Comment `/update-docs` to auto-append simple stubs for missing items.
        """).strip())

    return "\n".join(lines).strip()

def main():
    body = analyze()
    post_pr_comment(body)

if __name__ == "__main__":
    main()
