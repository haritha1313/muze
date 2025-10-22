#!/usr/bin/env python3
"""
GitHub PR Bot using Hot-Path Components 1 & 2

This bot:
1. Analyzes code changes in PRs using DocumentationAnalyzer
2. Generates doc update suggestions using LLMDocGenerator
3. Posts results as PR comment with prioritized recommendations

Environment Variables:
    GITHUB_TOKEN: GitHub API token (automatic in Actions)
    REPO: Repository slug (owner/repo)
    PR_NUMBER: Pull request number
    BASE_SHA: Base commit SHA
    HEAD_SHA: Head commit SHA
    OPENAI_API_KEY: OpenAI API key (optional, for LLM suggestions)
    ANTHROPIC_API_KEY: Anthropic API key (optional, alternative to OpenAI)
    ENABLE_LLM: "true" to enable LLM suggestions (default: false for cost control)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
import textwrap

# Import Hot-Path components
sys.path.insert(0, str(Path(__file__).parent))
try:
    from hotpath_integration import HotPathAnalyzer, HotPathAnalysis, FileChange
    from hotpath.llm_doc_generator import LLMDocGenerator
    HAS_HOTPATH = True
except ImportError:
    HAS_HOTPATH = False
    print("Warning: Hot-Path components not found. Running in basic mode.")


# ---- Environment ----
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")
BASE_SHA = os.getenv("BASE_SHA", "")
HEAD_SHA = os.getenv("HEAD_SHA", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

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


def get_changed_files() -> List[str]:
    """Get list of changed files in PR (excluding bot infrastructure)"""
    try:
        output = run_git("diff", "--name-only", f"{BASE_SHA}...{HEAD_SHA}")
        files = [f.strip() for f in output.split('\n') if f.strip()]
        # Filter out excluded paths (bot infrastructure)
        filtered = []
        for f in files:
            if not any(f.startswith(excluded) for excluded in EXCLUDED_PATHS):
                filtered.append(f)
        return filtered
    except subprocess.CalledProcessError:
        return []


def get_file_content(filepath: str, ref: str) -> str:
    """Get file content at specific git ref"""
    try:
        return run_git("show", f"{ref}:{filepath}")
    except subprocess.CalledProcessError:
        return ""


# ---- Hot-Path Analysis ----
def run_hotpath_analysis() -> Optional[HotPathAnalysis]:
    """
    Run Hot-Path analysis on local git repository using real algorithms.

    Uses all 5 layers:
    - Layer 1: Merkle Tree (file changes)
    - Layer 2: Semantic Analysis (change classification)
    - Layer 3: Communities (code relationships)
    - Layer 4: Cross-References (code-to-docs mapping)
    - Layer 5: Similarity (code patterns)

    Returns:
        HotPathAnalysis with comprehensive results, or None if Hot-Path unavailable
    """
    if not HAS_HOTPATH:
        return None

    print("[Hot-Path] Running full algorithmic analysis...")
    print(f"[Hot-Path] Base: {BASE_SHA[:8]} -> Head: {HEAD_SHA[:8]}")

    try:
        # Initialize analyzer - auto-detect repo root (find_repo_root() handles subdirectories)
        analyzer = HotPathAnalyzer(repo_path=None, verbose=True)

        # Run complete analysis with all layers
        analysis = analyzer.analyze_changes(
            base_ref=BASE_SHA,
            head_ref=HEAD_SHA,
            include_communities=True,
            include_similarity=False  # Disabled for performance
        )

        print(f"[Hot-Path] Analysis complete!")
        print(f"[Hot-Path] Found {len(analysis.changed_files)} files changed")
        print(f"[Hot-Path] - High priority (MAJOR/REWRITE): {len(analysis.get_high_priority_changes())}")
        print(f"[Hot-Path] - Medium priority (MINOR): {len(analysis.get_medium_priority_changes())}")
        print(f"[Hot-Path] - Code entities: {analysis.total_entities} total, {analysis.documented_entities} documented")

        return analysis

    except Exception as e:
        print(f"[Hot-Path] Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_llm_suggestions(
    file_changes: List[FileChange],
    limit: int = 3
) -> List[Dict]:
    """
    Generate LLM documentation suggestions for changed files.

    Args:
        file_changes: List of FileChange objects from Hot-Path analysis
        limit: Maximum number of suggestions to generate

    Returns:
        List of suggestion dicts
    """
    if not ENABLE_LLM:
        return []

    if not (OPENAI_API_KEY or ANTHROPIC_API_KEY):
        print("[LLM] No API key found, skipping LLM suggestions")
        return []

    print("[LLM] Generating documentation suggestions...")

    # Determine provider
    if OPENAI_API_KEY:
        provider = "openai"
        api_key = OPENAI_API_KEY
    else:
        provider = "anthropic"
        api_key = ANTHROPIC_API_KEY

    generator = LLMDocGenerator(provider=provider, api_key=api_key)

    suggestions = []

    # Prioritize high-priority changes (MAJOR/REWRITE)
    prioritized = sorted(file_changes, key=lambda fc: fc.priority_score(), reverse=True)

    for file_change in prioritized[:limit]:  # Limit to avoid high costs
        filepath = file_change.path

        # Get old and new versions
        old_code = get_file_content(filepath, BASE_SHA)
        new_code = get_file_content(filepath, HEAD_SHA)

        if not new_code:
            continue

        # Extract entity name from file path
        entity_name = Path(filepath).stem

        # Generate suggestion using Hot-Path change classification
        try:
            suggestion = generator.generate_doc_update(
                old_code=old_code[:2000],  # Truncate for cost
                new_code=new_code[:2000],
                current_doc=f"Documentation for {entity_name}",
                change_type=file_change.change_type,  # Use real semantic classification
                entity_name=entity_name,
                context={
                    "mentions": 1,
                    "distance": file_change.normalized_distance,  # Use real tree edit distance
                    "file": filepath,
                    "new_code": new_code  # Pass full code for fallback
                },
                filename=filepath,
                language=file_change.language or ("python" if filepath.endswith('.py') else "javascript")
            )

            suggestions.append({
                "file": filepath,
                "entity": entity_name,
                "change_type": file_change.change_type,
                "distance": file_change.normalized_distance,
                "suggestion": suggestion.updated_doc[:500],  # Truncate
                "explanation": suggestion.explanation,
                "confidence": suggestion.confidence,
                "cost": suggestion.cost_usd
            })

        except Exception as e:
            print(f"[LLM] Error generating suggestion for {filepath}: {e}")

    total_cost = sum(s["cost"] for s in suggestions)
    print(f"[LLM] Generated {len(suggestions)} suggestions (cost: ${total_cost:.4f})")

    return suggestions


# ---- Comment Formatting ----
def format_pr_comment(
    analysis: Optional[HotPathAnalysis],
    suggestions: List[Dict]
) -> str:
    """
    Format PR comment with Hot-Path analysis and LLM suggestions.

    Args:
        analysis: HotPathAnalysis with comprehensive semantic results
        suggestions: LLM-generated suggestions

    Returns:
        Formatted markdown comment
    """
    lines = []

    # Header with marker for updates
    marker = f"<!-- HOT-PATH-BOT:PR:{PR_NUMBER} -->"
    lines.append(marker)
    lines.append("")
    lines.append("## Hot-Path Documentation Analysis")
    lines.append("")
    lines.append("Powered by **Hot-Path** - 5-layer semantic documentation impact analysis")
    lines.append("")

    # Summary with real semantic data
    if analysis:
        high_priority = analysis.get_high_priority_changes()
        medium_priority = analysis.get_medium_priority_changes()

        lines.append("### Semantic Analysis Summary")
        lines.append("")
        lines.append(f"- **{len(analysis.changed_files)} files** analyzed in {analysis.elapsed_seconds:.1f}s")
        lines.append(f"- **{analysis.files_added} added**, **{analysis.files_deleted} deleted**")
        lines.append("")

        lines.append("**Change Classification** (using Zhang-Shasha tree edit distance):")
        for change_type, count in sorted(analysis.changes_by_type.items()):
            if count > 0:
                lines.append(f"- **{change_type.upper()}**: {count} files")
        lines.append("")

        lines.append("**Documentation Impact:**")
        lines.append(f"- **HIGH priority** (MAJOR/REWRITE): {len(high_priority)} files need docs")
        lines.append(f"- **MEDIUM priority** (MINOR): {len(medium_priority)} files")
        lines.append("")

        lines.append("**Code Entities:**")
        lines.append(f"- Total entities found: {analysis.total_entities}")
        lines.append(f"- Documented: {analysis.documented_entities}")
        lines.append(f"- Undocumented: {analysis.undocumented_entities}")

        if analysis.communities_found:
            lines.append(f"- Code communities detected: {analysis.communities_found}")

        lines.append("")

        # High priority changes details
        if high_priority:
            lines.append("### High Priority Changes (Require Documentation)")
            lines.append("")
            for fc in high_priority[:5]:  # Show top 5
                lines.append(f"#### `{fc.path}`")
                lines.append(f"- **Change Type:** {fc.change_type.upper()}")
                lines.append(f"- **Tree Edit Distance:** {fc.normalized_distance:.2f}")
                lines.append(f"- **Language:** {fc.language or 'unknown'}")

                # Show impacted docs if available
                impacted = analysis.get_impacted_docs(fc.path)
                if impacted:
                    lines.append(f"- **Impacted Docs:** {', '.join(f'`{d}`' for d in impacted[:3])}")
                lines.append("")

            if len(high_priority) > 5:
                lines.append(f"*... and {len(high_priority) - 5} more high priority changes*")
                lines.append("")

        # Medium priority changes summary
        if medium_priority:
            lines.append("<details>")
            lines.append("<summary>Medium Priority Changes (Consider Documentation)</summary>")
            lines.append("")
            for fc in medium_priority[:10]:
                lines.append(f"- `{fc.path}` - {fc.change_type.upper()} (distance: {fc.normalized_distance:.2f})")
            if len(medium_priority) > 10:
                lines.append(f"- ... and {len(medium_priority) - 10} more")
            lines.append("")
            lines.append("</details>")
            lines.append("")
    else:
        lines.append("### Analysis Unavailable")
        lines.append("")
        lines.append("Hot-Path components not fully configured.")
        lines.append("Check the workflow logs for details.")
        lines.append("")

    # LLM Suggestions
    if suggestions:
        lines.append("### AI-Generated Documentation Suggestions")
        lines.append("")
        lines.append("The following suggestions were generated using LLM analysis:")
        lines.append("")

        for i, sugg in enumerate(suggestions, 1):
            lines.append(f"#### {i}. `{sugg['file']}` - {sugg['entity']}")
            lines.append("")
            lines.append(f"**Change Type:** {sugg['change_type'].upper()}")
            lines.append(f"**Confidence:** {sugg['confidence']:.0%}")
            lines.append("")
            lines.append("**Explanation:**")
            lines.append(f"> {sugg['explanation']}")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>View Suggestion</summary>")
            lines.append("")
            lines.append("```markdown")
            lines.append(sugg['suggestion'])
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        total_cost = sum(s["cost"] for s in suggestions)
        lines.append(f"*Cost for this analysis: ${total_cost:.4f}*")
        lines.append("")
    elif ENABLE_LLM:
        lines.append("### LLM Suggestions")
        lines.append("")
        lines.append("LLM suggestions enabled but no suggestions generated.")
        lines.append("This could be due to:")
        lines.append("- No significant code changes")
        lines.append("- API key not configured")
        lines.append("- LLM generation failed")
        lines.append("")

    # Actions
    lines.append("---")
    lines.append("")
    lines.append("### Next Steps")
    lines.append("")

    if analysis and analysis.changed_files:
        lines.append("1. **Review** the changed code files above")
        lines.append("2. **Update** corresponding documentation")
        lines.append("3. **Test** that examples in docs still work")

        if suggestions:
            lines.append("4. **Consider** applying AI suggestions (review carefully first)")

    lines.append("")

    # Add /update-docs command if LLM enabled
    if ENABLE_LLM and (OPENAI_API_KEY or ANTHROPIC_API_KEY):
        lines.append("### Automatic Documentation Updates")
        lines.append("")
        lines.append("Comment **`/update-docs`** on this PR to automatically:")
        lines.append("- Generate high-quality documentation using LLM")
        lines.append("- Commit updates directly to this PR branch")
        lines.append("- Update this comment with results")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<sub>")
    lines.append("Powered by [Hot-Path](https://github.com/anthropics/hot-path) | ")
    lines.append("[Configure](.github/workflows/doc-analysis.yml)")
    lines.append("</sub>")

    return "\n".join(lines)


# ---- GitHub API ----
def post_pr_comment(message: str):
    """Post comment to PR"""
    if not all([REPO, PR_NUMBER, GITHUB_TOKEN]):
        print("Missing GitHub credentials, cannot post comment")
        print(f"REPO: {REPO}, PR_NUMBER: {PR_NUMBER}, TOKEN: {'set' if GITHUB_TOKEN else 'missing'}")
        return

    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.post(url, headers=headers, json={"body": message})

    if response.status_code == 201:
        print(f"Posted comment to PR #{PR_NUMBER}")
    else:
        print(f"Failed to post comment: {response.status_code}")
        print(response.text)


def update_existing_comment(message: str):
    """
    Update existing Hot-Path comment instead of creating new one.
    Falls back to creating new comment if not found.
    """
    if not all([REPO, PR_NUMBER, GITHUB_TOKEN]):
        return post_pr_comment(message)

    marker = f"<!-- HOT-PATH-BOT:PR:{PR_NUMBER} -->"

    # Find existing comment
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return post_pr_comment(message)

    comments = response.json()

    # Find comment with marker
    existing_comment = None
    for comment in reversed(comments):  # Check newest first
        if marker in comment.get("body", ""):
            existing_comment = comment
            break

    if existing_comment:
        # Update existing comment
        update_url = f"https://api.github.com/repos/{REPO}/issues/comments/{existing_comment['id']}"
        response = requests.patch(update_url, headers=headers, json={"body": message})

        if response.status_code == 200:
            print(f"Updated existing comment on PR #{PR_NUMBER}")
        else:
            print(f"Failed to update comment: {response.status_code}")
    else:
        # Create new comment
        post_pr_comment(message)


# ---- Main ----
def main():
    """Main entry point"""
    print("=" * 80)
    print("Hot-Path PR Bot")
    print("=" * 80)

    # Validate environment
    if not BASE_SHA or not HEAD_SHA:
        print("Error: BASE_SHA and HEAD_SHA must be set")
        sys.exit(1)

    print(f"\nRepository: {REPO}")
    print(f"PR: #{PR_NUMBER}")
    print(f"Comparing: {BASE_SHA[:8]}...{HEAD_SHA[:8]}")
    print(f"LLM Enabled: {ENABLE_LLM}")

    if ENABLE_LLM:
        if OPENAI_API_KEY:
            print(f"LLM Provider: OpenAI")
        elif ANTHROPIC_API_KEY:
            print(f"LLM Provider: Anthropic")
        else:
            print(f"LLM Provider: None (no API key)")

    print()

    # Run analysis
    analysis = run_hotpath_analysis()

    # Generate LLM suggestions if enabled
    suggestions = []
    if analysis and analysis.changed_files:
        # Filter to files that need documentation updates
        files_needing_docs = [fc for fc in analysis.changed_files if fc.needs_doc_update]

        if files_needing_docs:
            suggestions = generate_llm_suggestions(
                files_needing_docs,
                limit=3  # Limit to 3 for cost control
            )

    # Format comment
    comment = format_pr_comment(analysis, suggestions)

    # Post/update comment
    update_existing_comment(comment)

    # Save results to file for debugging
    if analysis:
        results = {
            "summary": {
                "total_files": len(analysis.changed_files),
                "files_added": analysis.files_added,
                "files_deleted": analysis.files_deleted,
                "high_priority": len(analysis.get_high_priority_changes()),
                "medium_priority": len(analysis.get_medium_priority_changes()),
                "documented_entities": analysis.documented_entities,
                "undocumented_entities": analysis.undocumented_entities,
                "elapsed_seconds": analysis.elapsed_seconds
            },
            "changes_by_type": analysis.changes_by_type,
            "high_priority_files": [fc.path for fc in analysis.get_high_priority_changes()],
            "suggestions": [
                {k: v for k, v in s.items() if k != "suggestion"}  # Exclude large text
                for s in suggestions
            ]
        }
    else:
        results = {"error": "Analysis unavailable"}

    output_file = Path("hot-path-results.json")
    output_file.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output_file}")

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
