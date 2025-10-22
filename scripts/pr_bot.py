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

# Import Hot-Path components (these will be copied to target repo)
try:
    from doc_analyzer import DocumentationAnalyzer, Priority
    from llm_doc_generator import LLMDocGenerator
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
    """Get list of changed files in PR"""
    try:
        output = run_git("diff", "--name-only", f"{BASE_SHA}...{HEAD_SHA}")
        return [f.strip() for f in output.split('\n') if f.strip()]
    except subprocess.CalledProcessError:
        return []


def get_file_content(filepath: str, ref: str) -> str:
    """Get file content at specific git ref"""
    try:
        return run_git("show", f"{ref}:{filepath}")
    except subprocess.CalledProcessError:
        return ""


# ---- Hot-Path Analysis ----
def run_hotpath_analysis() -> Optional[Dict]:
    """
    Run Hot-Path analysis on local git repository.

    This adapts DocumentationAnalyzer to work with local git history
    instead of GitHub API calls.

    Returns:
        Dict with analysis results, or None if Hot-Path unavailable
    """
    if not HAS_HOTPATH:
        return None

    print("[Hot-Path] Analyzing code changes...")

    # For local analysis, we need to work with the git repo directly
    # rather than GitHub API. We'll use a simplified approach:

    changed_files = get_changed_files()

    # Basic analysis without full Hot-Path pipeline
    # (Full pipeline requires GitHub API; here we do minimal local analysis)

    results = {
        "changed_files": changed_files,
        "code_files": [f for f in changed_files if f.endswith(('.py', '.js', '.ts'))],
        "doc_files": [f for f in changed_files if f.endswith(('.md', '.rst', '.txt'))],
        "needs_analysis": True
    }

    print(f"[Hot-Path] Found {len(results['code_files'])} code files changed")

    return results


def generate_llm_suggestions(
    changed_files: List[str],
    limit: int = 3
) -> List[Dict]:
    """
    Generate LLM documentation suggestions for changed files.

    Args:
        changed_files: List of changed file paths
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

    for filepath in changed_files[:limit]:  # Limit to avoid high costs
        # Get old and new versions
        old_code = get_file_content(filepath, BASE_SHA)
        new_code = get_file_content(filepath, HEAD_SHA)

        if not new_code:
            continue

        # Determine change type (simplified)
        if not old_code:
            change_type = "major"  # New file
        elif len(new_code) > len(old_code) * 1.5:
            change_type = "major"
        elif len(new_code) < len(old_code) * 0.5:
            change_type = "major"
        else:
            change_type = "minor"

        # Extract entity name from file path
        entity_name = Path(filepath).stem

        # Generate suggestion
        try:
            suggestion = generator.generate_doc_update(
                old_code=old_code[:2000],  # Truncate for cost
                new_code=new_code[:2000],
                current_doc=f"Documentation for {entity_name}",
                change_type=change_type,
                entity_name=entity_name,
                context={
                    "mentions": 1,
                    "distance": 0.5,
                    "file": filepath
                },
                filename=filepath,
                language="python" if filepath.endswith('.py') else "javascript"
            )

            suggestions.append({
                "file": filepath,
                "entity": entity_name,
                "change_type": change_type,
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
    analysis: Optional[Dict],
    suggestions: List[Dict]
) -> str:
    """
    Format PR comment with Hot-Path analysis and LLM suggestions.

    Args:
        analysis: Hot-Path analysis results
        suggestions: LLM-generated suggestions

    Returns:
        Formatted markdown comment
    """
    lines = []

    # Header with marker for updates
    marker = f"<!-- HOT-PATH-BOT:PR:{PR_NUMBER} -->"
    lines.append(marker)
    lines.append("")
    lines.append("## 🔥 Hot-Path Documentation Analysis")
    lines.append("")
    lines.append("Powered by **Hot-Path** - AI-driven documentation impact analysis")
    lines.append("")

    # Summary
    if analysis:
        code_files = analysis.get("code_files", [])
        doc_files = analysis.get("doc_files", [])

        lines.append("### 📊 Summary")
        lines.append("")
        lines.append(f"- **{len(code_files)} code files** changed")
        lines.append(f"- **{len(doc_files)} doc files** changed")

        if code_files and not doc_files:
            lines.append("")
            lines.append("⚠️ **Code changed but no docs updated** - consider updating documentation")

        lines.append("")
        lines.append("### 📝 Changed Code Files")
        lines.append("")

        for f in code_files[:10]:  # Limit display
            lines.append(f"- `{f}`")

        if len(code_files) > 10:
            lines.append(f"- ... and {len(code_files) - 10} more")
    else:
        lines.append("### ℹ️ Basic Analysis")
        lines.append("")
        lines.append("Hot-Path components not fully configured.")
        lines.append("Enable full analysis by setting up GitHub API access.")

    lines.append("")

    # LLM Suggestions
    if suggestions:
        lines.append("### 🤖 AI-Generated Documentation Suggestions")
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
        lines.append("### 🤖 LLM Suggestions")
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
    lines.append("### 💡 Next Steps")
    lines.append("")

    if analysis and analysis.get("code_files"):
        lines.append("1. **Review** the changed code files above")
        lines.append("2. **Update** corresponding documentation")
        lines.append("3. **Test** that examples in docs still work")

        if suggestions:
            lines.append("4. **Consider** applying AI suggestions (review carefully first)")

    lines.append("")

    # Add /update-docs command if LLM enabled
    if ENABLE_LLM and (OPENAI_API_KEY or ANTHROPIC_API_KEY):
        lines.append("### 🤖 Automatic Documentation Updates")
        lines.append("")
        lines.append("Comment **`/update-docs`** on this PR to automatically:")
        lines.append("- Generate high-quality documentation using LLM")
        lines.append("- Commit updates directly to this PR branch")
        lines.append("- Update this comment with results")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<sub>")
    lines.append("🔥 Powered by [Hot-Path](https://github.com/anthropics/hot-path) | ")
    lines.append("⚙️ [Configure](.github/workflows/doc-analysis.yml)")
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
        print(f"✓ Posted comment to PR #{PR_NUMBER}")
    else:
        print(f"✗ Failed to post comment: {response.status_code}")
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
            print(f"✓ Updated existing comment on PR #{PR_NUMBER}")
        else:
            print(f"✗ Failed to update comment: {response.status_code}")
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
    if analysis and analysis.get("code_files"):
        suggestions = generate_llm_suggestions(
            analysis["code_files"],
            limit=3  # Limit to 3 for cost control
        )

    # Format comment
    comment = format_pr_comment(analysis, suggestions)

    # Post/update comment
    update_existing_comment(comment)

    # Save results to file for debugging
    results = {
        "analysis": analysis,
        "suggestions": [
            {k: v for k, v in s.items() if k != "suggestion"}  # Exclude large text
            for s in suggestions
        ]
    }

    output_file = Path("hot-path-results.json")
    output_file.write_text(json.dumps(results, indent=2))
    print(f"\n✓ Results saved to {output_file}")

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
