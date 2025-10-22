#!/usr/bin/env python3
"""
Hot-Path Analysis Using REAL Algorithms with Local Git

This version uses the actual Hot-Path semantic analysis, communities,
cross-references, and similarity algorithms - all running on local git
instead of requiring GitHub API.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add hotpath to path
sys.path.insert(0, str(Path(__file__).parent / "hotpath"))

from local_git_adapter import LocalGitAdapter, patch_pipeline_for_local_git
import pipeline
from doc_analyzer import DocumentationAnalyzer, Priority

# Environment
BASE_SHA = os.getenv("BASE_SHA", "HEAD~1")
HEAD_SHA = os.getenv("HEAD_SHA", "HEAD")


def analyze_pr_with_hotpath(
    base_ref: str,
    head_ref: str,
    repo_path: Optional[Path] = None
) -> Dict:
    """
    Run FULL Hot-Path analysis using local git.

    This uses ALL 5 layers:
    1. Merkle Tree - Detect changed files
    2. Semantic Analysis - Classify change severity
    3. Communities - Find related code clusters
    4. Cross-References - Map code entities to docs
    5. Similarity - Find similar code patterns

    Args:
        base_ref: Base git ref (e.g., "HEAD~1", "main")
        head_ref: Head git ref (e.g., "HEAD", "feature-branch")
        repo_path: Path to repository (defaults to finding from cwd)

    Returns:
        Dict with comprehensive analysis results
    """
    print("=" * 80)
    print("Hot-Path Analysis with Local Git (FULL ALGORITHMS)")
    print("=" * 80)

    # Initialize adapter
    adapter = LocalGitAdapter(repo_path)
    print(f"\nRepository: {adapter.repo_path}")
    print(f"Analyzing: {base_ref} -> {head_ref}")

    # Patch pipeline to use local git
    patch_pipeline_for_local_git(adapter)
    print("\n[+] Pipeline patched to use local git")

    # Create analyzer (using "local" as api_base triggers local mode)
    settings = pipeline.PipelineSettings(
        # Optimize for local analysis
        max_file_size_mb=10,
        max_analysis_time_seconds=120,  # 2 minute timeout
        tree_edit_distance_threshold=0.3,
        similarity_threshold=0.7,
        verbose=True
    )

    print("\n" + "-" * 80)
    print("Layer 2: Semantic Analysis (Tree Edit Distance)")
    print("-" * 80)

    # Run semantic analysis
    semantic_result = pipeline.analyze_semantic_diff(
        api_base="local",  # Special marker for local mode
        token=None,
        code_slug=str(adapter.repo_path),
        old_ref=base_ref,
        new_ref=head_ref,
        settings=settings
    )

    print(f"\n[+] Analyzed {semantic_result['files_analyzed']} files")
    print(f"    - Identical: {semantic_result['summary']['identical']}")
    print(f"    - Refactor: {semantic_result['summary']['refactor']}")
    print(f"    - Minor: {semantic_result['summary']['minor']}")
    print(f"    - Major: {semantic_result['summary']['major']}")
    print(f"    - Rewrite: {semantic_result['summary']['rewrite']}")
    print(f"    - Need doc update: {semantic_result['needs_doc_update_count']}")

    print("\n" + "-" * 80)
    print("Layer 3: Community Detection (Louvain)")
    print("-" * 80)

    # Run community analysis
    try:
        community_result = pipeline.analyze_communities(
            api_base="local",
            token=None,
            code_slug=str(adapter.repo_path),
            code_branch=head_ref,
            settings=settings
        )
        print(f"\n[+] Found {len(community_result['communities'])} code communities")
        print(f"    - Total nodes: {community_result['nodes']}")
        print(f"    - Total edges: {community_result['edges']}")
    except Exception as e:
        print(f"\n[!] Community analysis failed: {e}")
        community_result = {"communities": [], "nodes": 0, "edges": 0}

    print("\n" + "-" * 80)
    print("Layer 4: Cross-Reference Analysis (Aho-Corasick)")
    print("-" * 80)

    # Run cross-reference analysis
    try:
        crossref_result = pipeline.analyze_cross_references(
            api_base="local",
            token=None,
            code_slug=str(adapter.repo_path),
            code_branch=head_ref,
            docs_slug=str(adapter.repo_path),  # Same repo
            docs_branch=head_ref,
            settings=settings
        )
        print(f"\n[+] Cross-reference analysis complete")
        print(f"    - Total entities found: {crossref_result['total_entities']}")
        print(f"    - Documented entities: {crossref_result['documented_entities']}")
        print(f"    - Undocumented entities: {crossref_result['undocumented_entities']}")
    except Exception as e:
        print(f"\n[!] Cross-reference analysis failed: {e}")
        crossref_result = {
            "total_entities": 0,
            "entity_to_docs": {},
            "cross_reference_details": {"references_by_doc": {}}
        }

    print("\n" + "-" * 80)
    print("Layer 5: Similarity Analysis (MinHash + LSH)")
    print("-" * 80)

    # Run similarity analysis
    try:
        similarity_result = pipeline.analyze_similarity(
            api_base="local",
            token=None,
            code_slug=str(adapter.repo_path),
            code_branch=head_ref,
            docs_slug=str(adapter.repo_path),
            docs_branch=head_ref,
            settings=settings
        )
        print(f"\n[+] Similarity analysis complete")
        print(f"    - Files analyzed: {similarity_result['files']}")
        print(f"    - Candidate pairs: {similarity_result['candidates']}")
        print(f"    - Similar pairs found: {similarity_result['edges']}")
    except Exception as e:
        print(f"\n[!] Similarity analysis failed: {e}")
        similarity_result = {"files": 0, "edges": 0, "top_pairs": []}

    # Compile results
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    changes_by_priority = {
        "major": [],
        "minor": [],
        "other": []
    }

    for change in semantic_result.get("changes", []):
        if change["needs_doc_update"]:
            if change["change_type"] in ["major", "rewrite"]:
                changes_by_priority["major"].append(change)
            elif change["change_type"] == "minor":
                changes_by_priority["minor"].append(change)
            else:
                changes_by_priority["other"].append(change)

    print(f"\nFiles requiring documentation updates:")
    print(f"  - HIGH priority (MAJOR/REWRITE): {len(changes_by_priority['major'])}")
    print(f"  - MEDIUM priority (MINOR): {len(changes_by_priority['minor'])}")
    print(f"  - LOW priority (other): {len(changes_by_priority['other'])}")

    if changes_by_priority["major"]:
        print(f"\n  High priority files:")
        for change in changes_by_priority["major"][:10]:
            print(f"    - {change['path']} ({change['change_type'].upper()}, distance: {change['normalized_distance']:.2f})")

    # Find which docs are impacted
    impacted_docs = set()
    for change in changes_by_priority["major"]:
        file_name = Path(change['path']).stem
        # Check cross-references
        for entity, docs in crossref_result.get("entity_to_docs", {}).items():
            if file_name.lower() in entity.lower():
                impacted_docs.update(docs)

    if impacted_docs:
        print(f"\n  Documentation files that may need updates:")
        for doc in sorted(impacted_docs)[:10]:
            print(f"    - {doc}")

    print("\n" + "=" * 80)

    return {
        "semantic": semantic_result,
        "communities": community_result,
        "cross_references": crossref_result,
        "similarity": similarity_result,
        "changes_by_priority": changes_by_priority,
        "impacted_docs": list(impacted_docs)
    }


def main():
    """Main entry point"""
    base = os.getenv("BASE_SHA", "HEAD~1")
    head = os.getenv("HEAD_SHA", "HEAD")

    result = analyze_pr_with_hotpath(base, head)

    # Save results
    import json
    output_file = Path("hotpath-analysis-full.json")
    with output_file.open("w") as f:
        # Make it JSON serializable
        clean_result = {
            "semantic_summary": result["semantic"]["summary"],
            "files_needing_docs": result["semantic"]["needs_doc_update_count"],
            "communities_found": len(result["communities"]["communities"]),
            "documented_entities": result["cross_references"]["documented_entities"],
            "undocumented_entities": result["cross_references"]["undocumented_entities"],
            "changes_by_priority": {
                "major": len(result["changes_by_priority"]["major"]),
                "minor": len(result["changes_by_priority"]["minor"]),
                "other": len(result["changes_by_priority"]["other"])
            },
            "impacted_docs": result["impacted_docs"]
        }
        json.dump(clean_result, f, indent=2)

    print(f"\n[+] Full results saved to: {output_file}")


if __name__ == "__main__":
    main()
