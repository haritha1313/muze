#!/usr/bin/env python3
"""
Hot-Path Enhanced Documentation Updater

Triggered by `/update-docs` comment on PR.
Uses LLM to generate high-quality documentation (not just stubs).

This is the Hot-Path version of update_docs.py with LLM-powered generation.

Environment Variables:
    GITHUB_TOKEN: GitHub API token
    REPO: Repository slug (owner/repo)
    PR_NUMBER: Pull request number
    BASE_SHA: Base commit SHA
    HEAD_SHA: Head commit SHA
    OPENAI_API_KEY: OpenAI API key (required for paid mode)
    ANTHROPIC_API_KEY: Alternative to OpenAI
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
import requests
import re

# Import Hot-Path components
sys.path.insert(0, str(Path(__file__).parent / "hotpath"))
from llm_doc_generator import LLMDocGenerator


# ---- Environment ----
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")
BASE_SHA = os.getenv("BASE_SHA", "")
HEAD_SHA = os.getenv("HEAD_SHA", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")
DOCS_EXTRAS = [p.strip() for p in os.getenv("DOCS_EXTRAS", "README.md").split(",") if p.strip()]

CODE_EXTS = {".py", ".js", ".ts"}


# ---- Git Helpers ----
def run_git(*args, check=True) -> str:
    """Run git command and return stdout"""
    result = subprocess.run(
        ["git", *args],
        check=check,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def git_config():
    """Configure git for commits"""
    run_git("config", "user.name", "hot-path-bot")
    run_git("config", "user.email", "bot@hotpath.dev")


def get_changed_files() -> Dict[str, str]:
    """Get changed files with their status"""
    files = {}
    output = run_git("diff", "--name-status", f"{BASE_SHA}...{HEAD_SHA}")
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        files[path] = status
    return files


def get_file_content(filepath: str, ref: str) -> str:
    """Get file content at specific ref"""
    try:
        return run_git("show", f"{ref}:{filepath}")
    except subprocess.CalledProcessError:
        return ""


# ---- Code Analysis ----
def is_code_file(path: str) -> bool:
    return Path(path).suffix in CODE_EXTS


def extract_functions_from_code(code: str) -> Set[str]:
    """Extract function names from code"""
    import ast

    if not code:
        return set()

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()

    functions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.add(node.name)

    return functions


def analyze_code_changes() -> List[Dict]:
    """
    Analyze code changes and determine what needs documentation.

    Returns:
        List of dicts with: file, entity, old_code, new_code, change_type
    """
    changed_files = get_changed_files()
    code_files = [f for f in changed_files if is_code_file(f)]

    changes = []

    for filepath in code_files:
        old_code = get_file_content(filepath, BASE_SHA)
        new_code = get_file_content(filepath, HEAD_SHA)

        if not new_code:  # File deleted
            continue

        old_funcs = extract_functions_from_code(old_code)
        new_funcs = extract_functions_from_code(new_code)

        # New functions
        added = new_funcs - old_funcs

        # Modified functions (heuristic: if code changed significantly)
        modified = set()
        if old_code and new_code:
            if len(new_code) != len(old_code):  # Simple change detection
                # Functions that exist in both but file changed
                modified = old_funcs & new_funcs

        # Determine change types
        for func in added:
            changes.append({
                "file": filepath,
                "entity": func,
                "old_code": "",
                "new_code": extract_function_code(new_code, func),
                "change_type": "major",  # New function is major
                "reason": "added"
            })

        for func in modified:
            changes.append({
                "file": filepath,
                "entity": func,
                "old_code": extract_function_code(old_code, func),
                "new_code": extract_function_code(new_code, func),
                "change_type": "minor",  # Modified is minor (could be major)
                "reason": "modified"
            })

    return changes


def extract_function_code(code: str, func_name: str) -> str:
    """Extract code for a specific function"""
    import ast

    try:
        tree = ast.parse(code)
    except:
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            # Get the source code for this function
            lines = code.split('\n')
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
            return '\n'.join(lines[start:end])

    return ""


# ---- Documentation Loading ----
def load_current_docs() -> Dict[str, str]:
    """Load current documentation files"""
    docs = {}

    # Load extra docs (README, etc)
    for extra in DOCS_EXTRAS:
        p = Path(extra)
        if p.exists() and p.is_file():
            try:
                docs[str(p)] = p.read_text(encoding="utf-8", errors="ignore")
            except:
                pass

    # Load docs directory
    docs_path = Path(DOCS_DIR)
    if docs_path.exists():
        for md_file in list(docs_path.rglob("*.md")) + list(docs_path.rglob("*.mdx")):
            try:
                docs[str(md_file)] = md_file.read_text(encoding="utf-8", errors="ignore")
            except:
                pass

    return docs


def is_entity_documented(entity: str, docs: Dict[str, str]) -> bool:
    """Check if entity is mentioned in docs"""
    pattern = re.compile(rf"(^|\W){re.escape(entity)}(\W|$)")
    for content in docs.values():
        if pattern.search(content):
            return True
    return False


def find_best_doc_file(filepath: str) -> str:
    """Determine best documentation file for code file"""
    module = Path(filepath).stem

    # Try docs/<module>.md
    prefer = Path(DOCS_DIR) / f"{module}.md"
    if prefer.exists():
        return str(prefer)

    # Try README.md
    if Path("README.md").exists():
        return "README.md"

    # Create new doc file
    return str(prefer)


# ---- LLM Documentation Generation ----
def generate_llm_documentation(changes: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Generate documentation for changes using LLM.

    Returns:
        Dict mapping doc_file -> list of generated sections
    """
    if not (OPENAI_API_KEY or ANTHROPIC_API_KEY):
        print("ERROR: No LLM API key configured!")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY for paid mode.")
        sys.exit(1)

    # Determine provider
    if OPENAI_API_KEY:
        provider = "openai"
        api_key = OPENAI_API_KEY
        print(f"Using OpenAI for documentation generation...")
    else:
        provider = "anthropic"
        api_key = ANTHROPIC_API_KEY
        print(f"Using Anthropic Claude for documentation generation...")

    generator = LLMDocGenerator(
        provider=provider,
        api_key=api_key,
        temperature=0.3,
        max_tokens=2000
    )

    # Load current docs
    current_docs = load_current_docs()

    # Group changes by target doc file
    grouped: Dict[str, List[Dict]] = {}

    print(f"\nGenerating documentation for {len(changes)} changes...")

    for i, change in enumerate(changes, 1):
        print(f"  [{i}/{len(changes)}] {change['file']}::{change['entity']}...", end=" ")

        # Check if already documented
        if is_entity_documented(change['entity'], current_docs):
            print("already documented, skipping")
            continue

        # Find target doc file
        target_doc = find_best_doc_file(change['file'])

        # Get current doc content for context
        current_doc_content = current_docs.get(target_doc, f"# {Path(target_doc).stem} API Reference\n\n")

        # Generate documentation
        try:
            suggestion = generator.generate_doc_update(
                old_code=change['old_code'],
                new_code=change['new_code'],
                current_doc=current_doc_content,
                change_type=change['change_type'],
                entity_name=change['entity'],
                context={
                    "mentions": 0,
                    "file": change['file'],
                    "reason": change['reason']
                },
                filename=change['file'],
                language="python"
            )

            print(f"✓ (confidence: {suggestion.confidence:.0%}, cost: ${suggestion.cost_usd:.4f})")

            # Store generated content
            if target_doc not in grouped:
                grouped[target_doc] = []

            grouped[target_doc].append({
                "entity": change['entity'],
                "content": suggestion.updated_doc,
                "explanation": suggestion.explanation,
                "confidence": suggestion.confidence,
                "file": change['file']
            })

        except Exception as e:
            print(f"✗ Error: {e}")

    return grouped


# ---- Documentation Writing ----
def append_documentation(doc_file: str, sections: List[Dict]):
    """Append generated documentation to file"""
    doc_path = Path(doc_file)
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    if doc_path.exists():
        existing = doc_path.read_text(encoding="utf-8")
    else:
        # Create new file with header
        existing = f"# {doc_path.stem.replace('_', ' ').title()}\n\n"

    # Append new sections
    new_content = existing

    if "## API Reference" not in existing:
        new_content += "\n\n## API Reference\n\n"

    for section in sections:
        # Add a separator and the new content
        new_content += f"\n### {section['entity']}\n\n"
        new_content += f"*Source: `{section['file']}`*\n\n"
        new_content += section['content']
        new_content += "\n\n"

    # Write back
    doc_path.write_text(new_content, encoding="utf-8")
    print(f"  ✓ Updated {doc_file}")


# ---- GitHub Integration ----
def update_bot_comment(commit_sha: str, stats: Dict):
    """Update the original Hot-Path comment with success message"""
    if not all([REPO, PR_NUMBER, GITHUB_TOKEN]):
        return

    marker = f"<!-- HOT-PATH-BOT:PR:{PR_NUMBER} -->"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Find existing comment
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return

    comments = response.json()

    # Find Hot-Path comment
    target_comment = None
    for comment in reversed(comments):
        if marker in comment.get("body", ""):
            target_comment = comment
            break

    if not target_comment:
        return

    # Append success message
    total_cost = stats.get("total_cost", 0)
    sections_added = stats.get("sections_added", 0)
    files_updated = stats.get("files_updated", 0)

    update_msg = f"""

---

### ✅ Documentation Updated!

**Commit:** `{commit_sha}`

**Statistics:**
- 📝 {sections_added} documentation sections generated
- 📄 {files_updated} files updated
- 💰 Cost: ${total_cost:.4f}
- 🤖 Generated using {stats.get('provider', 'LLM')}

The documentation has been automatically updated based on your code changes.
Review the commit and adjust as needed.
"""

    new_body = target_comment["body"] + update_msg

    update_url = f"https://api.github.com/repos/{REPO}/issues/comments/{target_comment['id']}"
    requests.patch(update_url, headers=headers, json={"body": new_body})

    print(f"\n✓ Updated PR comment")


# ---- Main ----
def main():
    print("=" * 80)
    print("Hot-Path Enhanced Documentation Updater (LLM-Powered)")
    print("=" * 80)

    # Validate environment
    if not (OPENAI_API_KEY or ANTHROPIC_API_KEY):
        print("\n❌ ERROR: No LLM API key configured!")
        print("\nPaid mode requires an API key:")
        print("  - Set OPENAI_API_KEY for OpenAI (recommended)")
        print("  - Set ANTHROPIC_API_KEY for Anthropic Claude")
        print("\nAdd as GitHub Secret in your repository settings.")
        sys.exit(1)

    if not BASE_SHA or not HEAD_SHA:
        print("\n❌ ERROR: BASE_SHA and HEAD_SHA must be set")
        sys.exit(1)

    print(f"\nRepository: {REPO}")
    print(f"PR: #{PR_NUMBER}")
    print(f"Comparing: {BASE_SHA[:8]}...{HEAD_SHA[:8]}")

    # Analyze changes
    print("\n" + "-" * 80)
    print("Step 1: Analyzing code changes...")
    print("-" * 80)

    changes = analyze_code_changes()

    if not changes:
        print("\n✓ No undocumented code changes found.")
        print("All functions are either already documented or unchanged.")
        return

    print(f"\nFound {len(changes)} functions needing documentation:")
    for change in changes:
        print(f"  - {change['file']}::{change['entity']} ({change['reason']})")

    # Generate documentation
    print("\n" + "-" * 80)
    print("Step 2: Generating documentation with LLM...")
    print("-" * 80)

    generated = generate_llm_documentation(changes)

    if not generated:
        print("\n✓ All functions are already documented.")
        return

    print(f"\nGenerated documentation for {sum(len(v) for v in generated.values())} functions")

    # Write documentation
    print("\n" + "-" * 80)
    print("Step 3: Writing documentation files...")
    print("-" * 80)

    total_cost = 0.0
    sections_added = 0

    for doc_file, sections in generated.items():
        append_documentation(doc_file, sections)
        sections_added += len(sections)
        # Note: Cost tracking would need to be added to generator

    # Commit changes
    print("\n" + "-" * 80)
    print("Step 4: Committing changes...")
    print("-" * 80)

    git_config()

    # Stage changes
    run_git("add", DOCS_DIR)
    for extra in DOCS_EXTRAS:
        if Path(extra).exists():
            run_git("add", extra)

    # Create commit
    commit_msg = f"""docs: AI-generated documentation updates

Generated documentation for {sections_added} functions using Hot-Path LLM.

Files updated:
{chr(10).join(f'  - {f}' for f in generated.keys())}

🤖 Generated with Hot-Path + LLM
"""

    try:
        run_git("commit", "-m", commit_msg)
        print("✓ Changes committed")
    except subprocess.CalledProcessError:
        print("✓ No changes to commit (docs may already be up to date)")
        return

    # Push changes
    try:
        run_git("push")
        print("✓ Changes pushed to PR branch")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to push: {e}")
        sys.exit(1)

    # Get commit SHA
    commit_sha = run_git("rev-parse", "--short", "HEAD")

    # Update bot comment
    stats = {
        "total_cost": total_cost,
        "sections_added": sections_added,
        "files_updated": len(generated),
        "provider": "OpenAI" if OPENAI_API_KEY else "Anthropic"
    }

    update_bot_comment(commit_sha, stats)

    # Summary
    print("\n" + "=" * 80)
    print("✅ Documentation Update Complete!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Commit: {commit_sha}")
    print(f"  - Sections added: {sections_added}")
    print(f"  - Files updated: {len(generated)}")
    print(f"  - Provider: {stats['provider']}")
    print(f"\nView changes: https://github.com/{REPO}/pull/{PR_NUMBER}")


if __name__ == "__main__":
    main()
