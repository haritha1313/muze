import ast
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set
import requests
import textwrap

REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")
BASE_SHA = os.getenv("BASE_SHA")
HEAD_SHA = os.getenv("HEAD_SHA")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")
DOCS_EXTRAS = [p.strip() for p in os.getenv("DOCS_EXTRAS", "README.md").split(",") if p.strip()]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

CODE_EXTS = {".py"}  # extend later if needed

# ---------- git helpers ----------

def run(cmd: List[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def diff_name_status(base: str, head: str) -> List[Tuple[str, str]]:
    """
    Returns list of (status, path).
    Status: A,M,D,R... from --name-status
    """
    out = run(["git", "diff", "--name-status", f"{base}...{head}"]).strip()
    rows = []
    if out:
        for line in out.splitlines():
            parts = line.split("\t")
            status = parts[0]
            # handle renames: "R100\told\tnew"
            path = parts[-1]
            rows.append((status, path))
    return rows

def git_show(sha: str, path: str) -> str:
    try:
        return run(["git", "show", f"{sha}:{path}"])
    except subprocess.CalledProcessError:
        return ""  # file might not exist at base

# ---------- code parsing ----------

def list_changed_files() -> Dict[str, str]:
    """
    Map path -> status (A/M/D/R*). Only files we care about.
    """
    files = {}
    for status, path in diff_name_status(BASE_SHA, HEAD_SHA):
        files[path] = status
    return files

def is_code_file(p: str) -> bool:
    return Path(p).suffix in CODE_EXTS

def is_docs_file(p: str) -> bool:
    if any(Path(p).match(extra) or Path(p).name == extra for extra in DOCS_EXTRAS):
        return True
    return p.startswith(f"{DOCS_DIR}/") and Path(p).suffix.lower() in {".md", ".mdx"}

def parse_functions_from_source(src: str) -> Set[str]:
    """
    Return a set of function "signatures" like: name(arg_count)
    This is a simple, stable signal to compare base vs head.
    """
    if not src:
        return set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()

    fns = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # count only non-self/cls args for clarity
            args = [a.arg for a in node.args.args]
            if args and args[0] in {"self", "cls"}:
                args = args[1:]
            sig = f"{node.name}({len(args)})"
            fns.add(sig)
    return fns

def parse_top_level_names(src: str) -> Set[str]:
    """
    Also capture top-level functions by name only. This helps doc matching.
    """
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

# ---------- docs scanning ----------

def load_docs_at_head() -> Dict[str, str]:
    docs = {}
    for extra in DOCS_EXTRAS:
        p = Path(extra)
        if p.exists() and p.is_file():
            try:
                docs[str(p)] = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    d = Path(DOCS_DIR)
    if d.exists():
        for md in d.rglob("*.md"):
            try:
                docs[str(md)] = md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
        for md in d.rglob("*.mdx"):
            try:
                docs[str(md)] = md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    return docs

def name_mentioned_in_docs(name: str, docs_map: Dict[str, str]) -> List[str]:
    """
    Simple mention check: backticks, headings, code blocks, plain text.
    """
    hits = []
    # word boundary but allow backticks or underscores around the name
    pat = re.compile(rf"(^|\W){re.escape(name)}(\W|$)")
    for path, content in docs_map.items():
        if pat.search(content):
            hits.append(path)
    return hits

# ---------- main analysis ----------

def analyze() -> str:
    changed = list_changed_files()
    code_changed = [p for p in changed if is_code_file(p)]
    docs_changed = [p for p in changed if is_docs_file(p)]

    # Build function-level diff for each changed code file
    docs_map = load_docs_at_head()

    rows = []
    missing_docs_total = 0
    for path in code_changed:
        head_src = Path(path).read_text(encoding="utf-8", errors="ignore") if Path(path).exists() else ""
        base_src = git_show(BASE_SHA, path)

        base_sigs = parse_functions_from_source(base_src)
        head_sigs = parse_functions_from_source(head_src)

        base_names = parse_top_level_names(base_src)
        head_names = parse_top_level_names(head_src)

        added = sorted(head_sigs - base_sigs)
        removed = sorted(base_sigs - head_sigs)
        possibly_modified = []
        # Heuristic: if a name exists in both, but signature changed (arg count), it will show as removed+added with same name.
        # Capture these pairs for clarity.
        base_by_name = {s.split("(")[0]: s for s in base_sigs}
        head_by_name = {s.split("(")[0]: s for s in head_sigs}
        for nm in set(base_by_name.keys()) & set(head_by_name.keys()):
            if base_by_name[nm] != head_by_name[nm]:
                possibly_modified.append((base_by_name[nm], head_by_name[nm]))

        # Doc coverage for added/modified functions
        added_names = [s.split("(")[0] for s in added]
        modified_names = [b.split("(")[0] for (b, _h) in possibly_modified]
        to_check = sorted(set(added_names + modified_names))

        doc_hits: Dict[str, List[str]] = {}
        missing: List[str] = []
        for nm in to_check:
            hits = name_mentioned_in_docs(nm, docs_map)
            if hits:
                doc_hits[nm] = hits
            else:
                missing.append(nm)

        missing_docs_total += len(missing)

        rows.append({
            "path": path,
            "added": added,
            "removed": removed,
            "modified": possibly_modified,
            "doc_hits": doc_hits,
            "missing": missing,
        })

    # Build summary comment
    lines = []
    lines.append("## 📚 Code vs Docs Analysis")
    lines.append("")
    if not code_changed:
        lines.append("No code files changed that we track.")
    else:
        lines.append("**Code files changed:**")
        for p in code_changed:
            lines.append(f"- `{p}` ({changed[p]})")
    lines.append("")
    if docs_changed:
        lines.append("**Docs files changed in this PR:**")
        for p in docs_changed:
            lines.append(f"- `{p}`")
    else:
        lines.append("**Docs files changed in this PR:** _none_")
    lines.append("")

    for r in rows:
        lines.append(f"### `{r['path']}`")
        if r["added"]:
            lines.append("**Added functions**")
            for s in r["added"]:
                lines.append(f"- `{s}`")
        if r["modified"]:
            lines.append("**Signature changes**")
            for before, after in r["modified"]:
                lines.append(f"- `{before}` ➜ `{after}`")
        if r["removed"]:
            lines.append("**Removed functions**")
            for s in r["removed"]:
                lines.append(f"- `{s}`")

        if r["doc_hits"]:
            lines.append("**Docs found**")
            for nm, hits in r["doc_hits"].items():
                preview = ", ".join(f"`{h}`" for h in sorted(hits)[:3])
                lines.append(f"- `{nm}` mentioned in {preview}")
        if r["missing"]:
            lines.append("**❌ Missing docs**")
            for nm in r["missing"]:
                # simple suggestion: try docs/<module>.md first, else README.md
                mod = Path(r["path"]).stem
                suggestion = f"{DOCS_DIR}/{mod}.md"
                if not Path(suggestion).exists():
                    suggestion = "README.md"
                lines.append(f"- `{nm}` ➜ consider updating `{suggestion}`")
        if not any([r["added"], r["modified"], r["removed"]]):
            lines.append("_No function-level changes detected._")
        lines.append("")

    if missing_docs_total == 0 and code_changed:
        lines.append("✅ All added/changed functions are referenced in docs.")
    elif code_changed:
        lines.append(textwrap.dedent(f"""
        ---
        💡 Tip: add a comment `/update-docs` (future step) to auto-append stubs for **{missing_docs_total}** missing items.
        """).strip())

    return "\n".join(lines).strip()

# ---------- post comment ----------

def post_pr_comment(body: str):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    resp = requests.post(url, headers=headers, json={"body": body})
    resp.raise_for_status()

if __name__ == "__main__":
    comment = analyze()
    post_pr_comment(comment)
