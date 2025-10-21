import os
import subprocess
from pathlib import Path

# Minimal generator. No external APIs. Safe for first demo.
def generate_doc_for_function(file_path: str, function_name: str) -> str:
    mod = Path(file_path).stem
    return f"""## {function_name}

Brief description.

**Parameters:**
- ...

**Returns:**
- ...

**Example:**
```python
from {mod} import {function_name}
# {function_name}(...)
```"""

# Use the existing analyzer to find undocumented functions
def analyze_undocumented():
    import analyze_pr as analyzer
    base_sha = os.getenv('BASE_SHA')
    head_sha = os.getenv('HEAD_SHA')
    changed = analyzer.get_changed_files(base_sha, head_sha)
    results = []
    py_files = [p for p in changed if p.endswith('.py')]
    for fpath in py_files:
        if not Path(fpath).exists():
            continue
        for fn in analyzer.extract_functions_py(fpath):
            if not analyzer.is_mentioned(fn):
                results.append({'file': fpath, 'function': fn})
    return results

def append_docs(doc_file: str, content: str):
    Path(doc_file).parent.mkdir(parents=True, exist_ok=True)
    with open(doc_file, 'a', encoding='utf-8') as f:
        f.write("\n\n## API Reference\n\n")
        f.write(content.strip())
        f.write("\n")

def git(cmd):
    subprocess.run(cmd, check=True)

def main():
    undocumented = analyze_undocumented()
    if not undocumented:
        print("No undocumented functions.")
        return

    target = 'README.md'  # simple target for demo
    blocks = [generate_doc_for_function(it['file'], it['function']) for it in undocumented]
    append_docs(target, "\n\n".join(blocks))

    git(['git', 'config', 'user.name', 'doc-bot'])
    git(['git', 'config', 'user.email', 'bot@example.com'])
    git(['git', 'add', target])
    git(['git', 'commit', '-m', 'docs: auto-generate documentation'])
    git(['git', 'push'])
    print(f"Updated {target}")

if __name__ == "__main__":
    main()
