import os
import sys
import subprocess
from pathlib import Path
import requests

# make scripts/ importable so we can reuse analyze_pr helpers
SCRIPTS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPTS_DIR))
import analyze_pr as analyzer  # noqa: E402

# env
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")  # passed from workflow
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

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
    module = Path(code_path).stem
    prefer = Path(DOCS_DIR) / f"{module}.md"
    if prefer.exists():
        return str(prefer)
    if Path("README.md").exists():
        return "README.md"
    return str(prefer)  # create docs/<module>.md if nothing else

def analyze_undocumented():
    changed_map = analyzer.list_changed_files()
    changed = list(changed_map.keys())
    results = []
    py_files = [p for p in changed if p.endswith(".py") and Path(p).exists()]
    for fpath in py_files:
        for fn in analyzer.extract_functions_py(fpath):
            if not analyzer.is_mentioned(fn):
                results.append({"file": fpath, "function": fn, "target_doc": suggest_doc_target(fpath)})
    return results

def append_blocks(grouped_updates):
    for target_doc, items in grouped_updates.items():
        p = Path(target_doc)
        p.parent.mkdir(parents=True, exist_ok=True)
        blocks = []
        for it in items:
            mod = Path(it["file"]).stem
            blocks.append(generate_stub(it["function"], mod))
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n\n## API Reference\n\n")
            f.write("\n\n".join(blocks))
            f.write("\n")

def git(*args):
    subprocess.run(["git", *args], check=True)

def update_same_comment(commit_sha: str):
    """Append a success line to the analysis comment with our hidden marker."""
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
    updates = analyze_undocumented()
    if not updates:
        print("No undocumented functions to update.")
        return

    grouped = {}
    for u in updates:
        grouped.setdefault(u["target_doc"], []).append(u)

    append_blocks(grouped)

    git("config", "user.name", "doc-bot")
    git("config", "user.email", "bot@example.com")
    # stage both docs dir and README.md (either may be touched)
    git("add", DOCS_DIR, "README.md")
    try:
        git("commit", "-m", "docs: auto-generate documentation stubs")
    except subprocess.CalledProcessError:
        print("Nothing to commit.")
        return
    git("push")

    commit_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    update_same_comment(commit_sha)

if __name__ == "__main__":
    main()
