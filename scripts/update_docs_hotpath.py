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
sys.path.insert(0, str(Path(__file__).parent))
from hotpath_integration import HotPathAnalyzer, HotPathAnalysis, FileChange
from hotpath.llm_doc_generator import LLMDocGenerator


# ---- Environment ----
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")
BASE_SHA = os.getenv("BASE_SHA", "")
HEAD_SHA = os.getenv("HEAD_SHA", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Find repository root (where .git directory is)
def find_repo_root() -> Path:
    """Find the repository root by looking for .git directory"""
    current = Path.cwd().resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    # Fallback: assume we're in scripts/ and go up one level
    script_dir = Path(__file__).parent.resolve()
    if script_dir.name == "scripts":
        return script_dir.parent
    return Path.cwd()

REPO_ROOT = find_repo_root()
DOCS_DIR_REL = os.getenv("DOCS_DIR", "docs")  # Relative path from repo root
DOCS_DIR = str(REPO_ROOT / DOCS_DIR_REL)  # Absolute path to docs directory

DOCS_EXTRAS_REL = [p.strip() for p in os.getenv("DOCS_EXTRAS", "README.md").split(",") if p.strip()]
DOCS_EXTRAS = [str(REPO_ROOT / p) for p in DOCS_EXTRAS_REL]  # Absolute paths

CODE_EXTS = {".py", ".js", ".ts"}

# Paths to exclude from documentation analysis (bot infrastructure, not product code)
EXCLUDED_PATHS = ["scripts/", ".github/", "tests/"]


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
    """Get changed files with their status (excluding bot infrastructure)"""
    files = {}
    output = run_git("diff", "--name-status", f"{BASE_SHA}...{HEAD_SHA}")
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        # Filter out excluded paths (bot infrastructure)
        if not any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
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


def analyze_code_changes() -> Tuple[HotPathAnalysis, List[Dict]]:
    """
    Analyze code changes using Hot-Path semantic analysis.

    Returns:
        Tuple of (HotPathAnalysis, List of entity-level changes for doc generation)
    """
    print("[Hot-Path] Running semantic analysis...")

    # Run Hot-Path analysis
    analyzer = HotPathAnalyzer(repo_path=REPO_ROOT, verbose=True)
    analysis = analyzer.analyze_changes(
        base_ref=BASE_SHA,
        head_ref=HEAD_SHA,
        include_communities=True,
        include_similarity=False
    )

    print(f"[Hot-Path] Analysis complete in {analysis.elapsed_seconds:.1f}s")
    print(f"[Hot-Path] Found {len(analysis.changed_files)} files changed")

    # Extract entity-level changes for documentation generation
    changes = []

    # Focus on high and medium priority changes
    priority_files = analysis.get_high_priority_changes() + analysis.get_medium_priority_changes()

    for file_change in priority_files:
        filepath = file_change.path

        # Skip if not a code file
        if not is_code_file(filepath):
            continue

        old_code = get_file_content(filepath, BASE_SHA)
        new_code = get_file_content(filepath, HEAD_SHA)

        if not new_code:  # File deleted
            continue

        # Extract functions from code
        old_funcs = extract_functions_from_code(old_code)
        new_funcs = extract_functions_from_code(new_code)

        # New functions
        added = new_funcs - old_funcs

        # Modified functions (for files that changed)
        modified = set()
        if old_code and new_code and file_change.change_type not in ["identical", "refactor"]:
            # Functions that exist in both but file changed significantly
            modified = old_funcs & new_funcs

        # Add entity-level changes using semantic classification from Hot-Path
        for func in added:
            changes.append({
                "file": filepath,
                "entity": func,
                "old_code": "",
                "new_code": extract_function_code(new_code, func),
                "change_type": file_change.change_type,  # Use Hot-Path classification
                "reason": "added",
                "distance": file_change.normalized_distance,
                "language": file_change.language
            })

        for func in modified:
            changes.append({
                "file": filepath,
                "entity": func,
                "old_code": extract_function_code(old_code, func),
                "new_code": extract_function_code(new_code, func),
                "change_type": file_change.change_type,  # Use Hot-Path classification
                "reason": "modified",
                "distance": file_change.normalized_distance,
                "language": file_change.language
            })

    return analysis, changes


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
    """Load current documentation files from repo root"""
    docs = {}

    # Load extra docs (README, etc) - DOCS_EXTRAS already has absolute paths
    for extra_path in DOCS_EXTRAS:
        p = Path(extra_path)
        if p.exists() and p.is_file():
            try:
                docs[str(p)] = p.read_text(encoding="utf-8", errors="ignore")
            except:
                pass

    # Load docs directory - DOCS_DIR is already absolute path
    docs_path = Path(DOCS_DIR)
    if docs_path.exists() and docs_path.is_dir():
        for md_file in list(docs_path.rglob("*.md")) + list(docs_path.rglob("*.mdx")):
            try:
                docs[str(md_file)] = md_file.read_text(encoding="utf-8", errors="ignore")
            except:
                pass
    else:
        print(f"Warning: Documentation directory does not exist: {docs_path}")

    return docs


def is_entity_documented(entity: str, docs: Dict[str, str]) -> bool:
    """Check if entity is mentioned in docs"""
    pattern = re.compile(rf"(^|\W){re.escape(entity)}(\W|$)")
    for content in docs.values():
        if pattern.search(content):
            return True
    return False


def find_best_doc_file(filepath: str) -> str:
    """Determine best documentation file for code file (always in docs/ at repo root)"""
    module = Path(filepath).stem

    # Try docs/<module>.md (DOCS_DIR is already absolute path to repo_root/docs)
    prefer = Path(DOCS_DIR) / f"{module}.md"
    if prefer.exists():
        return str(prefer)

    # Check if there's a general API reference doc
    api_ref = Path(DOCS_DIR) / "API-Reference.md"
    if api_ref.exists():
        return str(api_ref)

    # Create new doc file in docs/ (at repo root)
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

        # Generate documentation using Hot-Path enhanced context
        try:
            suggestion = generator.generate_doc_update(
                old_code=change['old_code'],
                new_code=change['new_code'],
                current_doc=current_doc_content,
                change_type=change['change_type'],  # From Hot-Path semantic analysis
                entity_name=change['entity'],
                context={
                    "mentions": 0,
                    "file": change['file'],
                    "reason": change['reason'],
                    "distance": change.get('distance', 0.5),  # Hot-Path tree edit distance
                    "new_code": change['new_code']  # Pass code for fallback
                },
                filename=change['file'],
                language=change.get('language') or "python"  # From Hot-Path language detection
            )

            print(f"OK (confidence: {suggestion.confidence:.0%}, cost: ${suggestion.cost_usd:.4f})")

            # Only use suggestions with reasonable confidence
            MIN_CONFIDENCE = 0.3  # 30% minimum confidence threshold

            if suggestion.confidence < MIN_CONFIDENCE:
                print(f"   Skipping due to low confidence ({suggestion.confidence:.0%} < {MIN_CONFIDENCE:.0%})")
                print(f"   Reason: {suggestion.explanation}")
                continue

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
            print(f"Error: {e}")

    return grouped


# ---- Documentation Writing ----
def append_documentation(doc_file: str, sections: List[Dict]):
    """Update or append generated documentation to file"""
    doc_path = Path(doc_file)
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    if doc_path.exists():
        existing = doc_path.read_text(encoding="utf-8")
    else:
        # Create new file with header
        existing = f"# {doc_path.stem.replace('_', ' ').title()}\n\n"

    # Ensure API Reference section exists
    if "## API Reference" not in existing:
        existing += "\n\n## API Reference\n\n"

    # Process each section - replace if exists, append if new
    new_content = existing

    for section in sections:
        entity_name = section['entity']

        # Build new section content
        new_section = f"### {entity_name}\n\n"
        new_section += f"*Source: `{section['file']}`*\n\n"
        new_section += section['content']

        # Try to find existing section for this entity
        # Look for patterns like "## entity_name" or "### entity_name"
        import re

        # Match heading followed by entity name (case insensitive)
        pattern = rf"(^|\n)(###+)\s+{re.escape(entity_name)}\s*\n(.*?)(?=\n##|\n###|\Z)"
        match = re.search(pattern, new_content, re.IGNORECASE | re.DOTALL)

        if match:
            # Replace existing section
            old_section = match.group(0)
            # Preserve the heading level from existing section
            heading_level = match.group(2)

            replacement = f"\n{heading_level} {entity_name}\n\n"
            replacement += f"*Source: `{section['file']}`*\n\n"
            replacement += section['content']

            new_content = new_content.replace(old_section, replacement)
            print(f"    Replaced existing section for {entity_name}")
        else:
            # Append new section
            # Find the end of API Reference section or end of file
            api_ref_match = re.search(r"## API Reference\s*\n", new_content)
            if api_ref_match:
                # Insert after API Reference heading
                insert_pos = api_ref_match.end()
                new_content = (
                    new_content[:insert_pos] +
                    "\n" + new_section + "\n\n" +
                    new_content[insert_pos:]
                )
            else:
                # Append at end
                new_content += "\n" + new_section + "\n\n"

            print(f"    Added new section for {entity_name}")

    # Write back
    doc_path.write_text(new_content, encoding="utf-8")
    print(f"  Updated {doc_file}")


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

### Documentation Updated!

**Commit:** `{commit_sha}`

**Statistics:**
- {sections_added} documentation sections generated
- {files_updated} files updated
- Cost: ${total_cost:.4f}
- Generated using {stats.get('provider', 'LLM')}

The documentation has been automatically updated based on your code changes.
Review the commit and adjust as needed.
"""

    new_body = target_comment["body"] + update_msg

    update_url = f"https://api.github.com/repos/{REPO}/issues/comments/{target_comment['id']}"
    requests.patch(update_url, headers=headers, json={"body": new_body})

    print(f"\nUpdated PR comment")


# ---- Main ----
def main():
    print("=" * 80)
    print("Hot-Path Enhanced Documentation Updater (LLM-Powered)")
    print("=" * 80)

    # Validate environment
    if not (OPENAI_API_KEY or ANTHROPIC_API_KEY):
        print("\nERROR: No LLM API key configured!")
        print("\nPaid mode requires an API key:")
        print("  - Set OPENAI_API_KEY for OpenAI (recommended)")
        print("  - Set ANTHROPIC_API_KEY for Anthropic Claude")
        print("\nAdd as GitHub Secret in your repository settings.")
        sys.exit(1)

    if not BASE_SHA or not HEAD_SHA:
        print("\nERROR: BASE_SHA and HEAD_SHA must be set")
        sys.exit(1)

    print(f"\nRepository: {REPO}")
    print(f"PR: #{PR_NUMBER}")
    print(f"Comparing: {BASE_SHA[:8]}...{HEAD_SHA[:8]}")
    print(f"\nPaths:")
    print(f"  Repo Root: {REPO_ROOT}")
    print(f"  Docs Directory: {DOCS_DIR}")
    print(f"  Extra Docs: {', '.join(DOCS_EXTRAS) if DOCS_EXTRAS else 'None'}")

    # Analyze changes
    print("\n" + "-" * 80)
    print("Step 1: Analyzing code changes with Hot-Path...")
    print("-" * 80)

    analysis, changes = analyze_code_changes()

    # Display Hot-Path analysis summary
    print(f"\nHot-Path Analysis Summary:")
    print(f"  - Files analyzed: {len(analysis.changed_files)}")
    print(f"  - Analysis time: {analysis.elapsed_seconds:.1f}s")
    print(f"\n  Change Classification:")
    for change_type, count in sorted(analysis.changes_by_type.items()):
        if count > 0:
            print(f"    - {change_type.upper()}: {count} files")
    print(f"\n  Documentation Impact:")
    print(f"    - HIGH priority: {len(analysis.get_high_priority_changes())} files")
    print(f"    - MEDIUM priority: {len(analysis.get_medium_priority_changes())} files")
    print(f"\n  Code Entities:")
    print(f"    - Total: {analysis.total_entities}")
    print(f"    - Documented: {analysis.documented_entities}")
    print(f"    - Undocumented: {analysis.undocumented_entities}")

    if not changes:
        print("\nNo undocumented code changes found.")
        print("All functions are either already documented or unchanged.")
        return

    print(f"\nFound {len(changes)} functions needing documentation:")
    for change in changes[:10]:  # Show first 10
        print(f"  - {change['file']}::{change['entity']} ({change['change_type']}, {change['reason']})")
    if len(changes) > 10:
        print(f"  ... and {len(changes) - 10} more")
    print(f"\nExcluded paths: {', '.join(EXCLUDED_PATHS)}")

    # Generate documentation
    print("\n" + "-" * 80)
    print("Step 2: Generating documentation with LLM...")
    print("-" * 80)

    generated = generate_llm_documentation(changes)

    if not generated:
        print("\nAll functions are already documented.")
        return

    print(f"\nGenerated documentation for {sum(len(v) for v in generated.values())} functions")

    # Write documentation
    print("\n" + "-" * 80)
    print(f"Step 3: Writing documentation files...")
    print(f"  Target directory: {DOCS_DIR}")
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

    # Change to repo root for git operations
    original_dir = Path.cwd()
    os.chdir(REPO_ROOT)

    try:
        # Stage changes (use relative paths from repo root)
        docs_rel = Path(DOCS_DIR).relative_to(REPO_ROOT)
        run_git("add", str(docs_rel))

        for extra_abs in DOCS_EXTRAS:
            extra_path = Path(extra_abs)
            if extra_path.exists():
                extra_rel = extra_path.relative_to(REPO_ROOT)
                run_git("add", str(extra_rel))

        # Create commit
        commit_msg = f"""docs: AI-generated documentation updates

Generated documentation for {sections_added} functions using Hot-Path LLM.

Files updated:
{chr(10).join(f'  - {Path(f).relative_to(REPO_ROOT)}' for f in generated.keys())}

Generated with Hot-Path + LLM
"""

        try:
            run_git("commit", "-m", commit_msg)
            print("Changes committed")
        except subprocess.CalledProcessError:
            print("No changes to commit (docs may already be up to date)")
            return

        # Push changes
        try:
            run_git("push")
            print("Changes pushed to PR branch")
        except subprocess.CalledProcessError as e:
            print(f"Failed to push: {e}")
            sys.exit(1)

    finally:
        # Restore original directory
        os.chdir(original_dir)

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
    print("Documentation Update Complete!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Commit: {commit_sha}")
    print(f"  - Sections added: {sections_added}")
    print(f"  - Files updated: {len(generated)}")
    print(f"  - Provider: {stats['provider']}")
    print(f"\nView changes: https://github.com/{REPO}/pull/{PR_NUMBER}")


if __name__ == "__main__":
    main()
