import os
import sys
import subprocess
from pathlib import Path
import requests
import re

# make scripts/ importable
SCRIPTS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPTS_DIR))
import analyze_pr as analyzer  # reuse helpers from analyze_pr.py

# ---- env ----
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")           # set in workflow
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

# ---- small helpers ----
def git(*args, check=True) -> str:
    out = subprocess.run(["git", *args], check=check, capture_output=True, text=True)
    return out.stdout.strip()

def generate_stub(func_name: str, module: str) -> str:
    return f"""## {func_name}

Brief description.

**Parameters:**
- ...

**Returns:**
- ...

**Example:**
```python
from {module} import {func_name}
# {func_name}(...)
```"""

def suggest_doc_target(code_path: str) -> str:
    """Prefer docs/<module>.md when present; otherwise README.md; else create module doc."""
    module = Path(code_path).stem
    prefer = Path(DOCS_DIR) / f"{module}.md"
    if prefer.exists():
        return str(prefer)
    if Path("README.md").exists():
        return "README.md"
    return str(prefer)

def names_not_mentioned(names):
    """Filter function names that are not mentioned in docs at HEAD."""
    docs_map = analyzer.load_docs_at_head()  # same logic as analyzer
    missing = []
    for nm in names:
        pat = re.compile(rf"(^|\W){re.escape(nm)}(\W|$)")
        if not any(pat.search(content) for content in docs_map.values()):
            missing.append(nm)
    return missing

# ---- core: compute exactly the same diff as the analyzer ----
def get_added_and_modified_names_for_changed_code():
    """
    Returns list of tuples (code_path, [names_needing_docs])
    Names are added or signature-modified vs BASE_SHA.
    """
    changed_map = analyzer.list_changed_files()  # path -> status
    code_changed = [p for p in changed_map if analyzer.is_code_file(p)]

    results = []
    for path in code_changed:
        head_src = Path(path).read_text(encoding="utf-8", errors="ignore") if Path(path).exists() else ""
        try:
            base_src = git("show", f"{analyzer.BASE_SHA}:{path}")
        except subprocess.CalledProcessError:
            base_src = ""

        base_sigs = analyzer.parse_functions_from_source(base_src)
        head_sigs = analyzer.parse_functions_from_source(head_src)

        added = sorted(head_sigs - base_sigs)
        base_by_name = {s.split("(")[0]: s for s in base_sigs}
        head_by_name = {s.split("(")[0]: s for s in head_sigs}
        modified_pairs = [(base_by_name[n], head_by_name[n])
                          for n in (set(base_by_name) & set(head_by_name))
                          if base_by_name[n] != head_by_name[n]]

        # names to check in docs = added names + modified names
        added_names = [s.split("(")[0] for s in added]
        modified_names = [after.split("(")[0] for (_before, after) in modified_pairs]
        to_check = sorted(set(added_names + modified_names))

        # Keep only names not currently mentioned in docs
        missing = names_not_mentioned(to_check)
        if missing:
            results.append((path, missing))
    return results

def append_stubs(grouped_updates):
    """grouped_updates: dict[target_doc -> list[(code_path, func_name)]]"""
    for target_doc, items in grouped_updates.items():
        p = Path(target_doc)
        p.parent.mkdir(parents=True, exist_ok=True)
        blocks = []
        for code_path, func_name in items:
            mod = Path(code_path).stem
            blocks.append(generate_stub(func_name, mod))
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n\n## API Reference\n\n")
            f.write("\n\n".join(blocks))
            f.write("\n")

def update_same_comment(commit_sha: str):
    """Append a success note to the original analysis comment (identified by hidden marker)."""
    if not (REPO and PR_NUMBER and GITHUB_TOKEN):
        print("Missing env to update comment. Skipping.")
        return
    marker = f"<!-- DOC-BOT:PR:{PR_NUMBER} -->"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    comments = resp.json()

    target = None
    for c in reversed(comments):  # newest first
        if (c.get("body") or "").startswith(marker):
            target = c
            break
    if not target:
        print("Could not find bot comment to update. Skipping.")
        return

    new_body = target["body"] + f"\n\n✅ Docs updated in commit `{commit_sha}`."
    patch_url = f"https://api.github.com/repos/{REPO}/issues/comments/{target['id']}"
    pr = requests.patch(patch_url, headers=headers, json={"body": new_body})
    pr.raise_for_status()
    print("Updated bot comment.")

def main():
    work = get_added_and_modified_names_for_changed_code()
    if not work:
        print("✅ No undocumented added/modified functions to update.")
        return

    # group by suggested doc target
    grouped = {}
    for code_path, missing_names in work:
        target_doc = suggest_doc_target(code_path)
        for nm in missing_names:
            grouped.setdefault(target_doc, []).append((code_path, nm))

    append_stubs(grouped)

    git("config", "user.name", "doc-bot")
    git("config", "user.email", "bot@example.com")
    git("add", DOCS_DIR, "README.md")
    try:
        git("commit", "-m", "docs: auto-generate documentation stubs")
    except subprocess.CalledProcessError:
        print("Nothing to commit.")
        return
    git("push")

    commit_sha = git("rev-parse", "--short", "HEAD")
    update_same_comment(commit_sha)

if __name__ == "__main__":
    main()
