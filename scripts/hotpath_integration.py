"""
Hot-Path Integration for CI/CD

Clean interface to use real Hot-Path algorithms with local git.
Used by both pr_bot.py and update_docs_hotpath.py.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

# Add hotpath to path
sys.path.insert(0, str(Path(__file__).parent / "hotpath"))

from local_git_adapter import LocalGitAdapter, patch_pipeline_for_local_git
import pipeline


@dataclass
class FileChange:
    """Information about a changed file"""
    path: str
    change_type: str  # "identical", "refactor", "minor", "major", "rewrite"
    distance: float
    normalized_distance: float
    needs_doc_update: bool
    language: Optional[str] = None

    def priority_score(self) -> int:
        """Get priority score (higher = more important)"""
        scores = {
            "rewrite": 5,
            "major": 4,
            "minor": 2,
            "refactor": 0,
            "identical": 0
        }
        return scores.get(self.change_type, 0)


@dataclass
class EntityReference:
    """Information about code entity documentation"""
    entity_name: str
    documented: bool
    doc_files: List[str]
    mention_count: int


@dataclass
class HotPathAnalysis:
    """Complete Hot-Path analysis results"""
    # Changed files with semantic analysis
    changed_files: List[FileChange]
    files_added: int
    files_deleted: int

    # Cross-reference data
    total_entities: int
    documented_entities: int
    undocumented_entities: int
    entity_references: Dict[str, EntityReference]

    # Community data
    communities_found: int

    # Statistics
    changes_by_type: Dict[str, int]
    elapsed_seconds: float

    def get_high_priority_changes(self) -> List[FileChange]:
        """Get changes that need documentation (MAJOR/REWRITE)"""
        return [
            f for f in self.changed_files
            if f.needs_doc_update and f.change_type in ["major", "rewrite"]
        ]

    def get_medium_priority_changes(self) -> List[FileChange]:
        """Get minor changes that may need documentation"""
        return [
            f for f in self.changed_files
            if f.needs_doc_update and f.change_type == "minor"
        ]

    def get_impacted_docs(self, file_path: str) -> List[str]:
        """Get documentation files that reference entities in this file"""
        file_name = Path(file_path).stem
        impacted = set()

        for entity_name, ref in self.entity_references.items():
            if file_name.lower() in entity_name.lower():
                impacted.update(ref.doc_files)

        return sorted(impacted)


class HotPathAnalyzer:
    """
    Hot-Path analyzer for CI/CD workflows.

    Uses all 5 layers:
    - Layer 1: Merkle Tree (file changes)
    - Layer 2: Semantic Analysis (change classification)
    - Layer 3: Communities (code relationships)
    - Layer 4: Cross-References (code-to-docs mapping)
    - Layer 5: Similarity (code patterns)
    """

    def __init__(self, repo_path: Optional[Path] = None, verbose: bool = False):
        """
        Initialize analyzer.

        Args:
            repo_path: Path to git repository (auto-detected if None)
            verbose: Enable verbose output
        """
        self.adapter = LocalGitAdapter(repo_path)
        self.verbose = verbose

        # Patch pipeline to use local git
        patch_pipeline_for_local_git(self.adapter)

        # Configure settings
        self.settings = pipeline.PipelineSettings(
            max_file_size_mb=10,
            max_analysis_time_seconds=120,
            tree_edit_distance_threshold=0.3,
            similarity_threshold=0.7,
            verbose=verbose
        )

    def analyze_changes(
        self,
        base_ref: str,
        head_ref: str,
        include_communities: bool = True,
        include_similarity: bool = False  # Expensive, disabled by default
    ) -> HotPathAnalysis:
        """
        Analyze changes between two refs using Hot-Path.

        Args:
            base_ref: Base git reference (e.g., "HEAD~1", "main")
            head_ref: Head git reference (e.g., "HEAD", "feature-branch")
            include_communities: Run community detection
            include_similarity: Run similarity analysis (slow)

        Returns:
            HotPathAnalysis with comprehensive results
        """
        if self.verbose:
            print(f"[Hot-Path] Analyzing: {base_ref} -> {head_ref}")

        import time
        start = time.time()

        # Layer 2: Semantic Analysis (most important)
        if self.verbose:
            print("[Hot-Path] Running semantic analysis...")

        semantic_result = pipeline.analyze_semantic_diff(
            api_base="local",
            token=None,
            code_slug=str(self.adapter.repo_path),
            old_ref=base_ref,
            new_ref=head_ref,
            settings=self.settings
        )

        # Convert to FileChange objects
        changed_files = []
        for change in semantic_result.get("changes", []):
            changed_files.append(FileChange(
                path=change["path"],
                change_type=change["change_type"],
                distance=change["distance"],
                normalized_distance=change["normalized_distance"],
                needs_doc_update=change["needs_doc_update"],
                language=change.get("language")
            ))

        # Layer 3: Communities (if requested)
        communities_found = 0
        if include_communities:
            if self.verbose:
                print("[Hot-Path] Running community detection...")
            try:
                community_result = pipeline.analyze_communities(
                    api_base="local",
                    token=None,
                    code_slug=str(self.adapter.repo_path),
                    code_branch=head_ref,
                    settings=self.settings
                )
                communities_found = len(community_result.get("communities", []))
            except Exception as e:
                if self.verbose:
                    print(f"[Hot-Path] Community detection failed: {e}")

        # Layer 4: Cross-References
        if self.verbose:
            print("[Hot-Path] Running cross-reference analysis...")

        try:
            crossref_result = pipeline.analyze_cross_references(
                api_base="local",
                token=None,
                code_slug=str(self.adapter.repo_path),
                code_branch=head_ref,
                docs_slug=str(self.adapter.repo_path),
                docs_branch=head_ref,
                settings=self.settings
            )

            # Build entity reference map
            entity_references = {}
            entity_to_docs = crossref_result.get("entity_to_docs", {})
            refs_by_doc = crossref_result.get("cross_reference_details", {}).get("references_by_doc", {})

            for entity, doc_list in entity_to_docs.items():
                # refs_by_doc already contains counts (integers), not lists
                mention_count = sum(
                    refs_by_doc.get(doc, {}).get(entity, 0)
                    for doc in doc_list
                )
                entity_references[entity] = EntityReference(
                    entity_name=entity,
                    documented=True,
                    doc_files=doc_list,
                    mention_count=mention_count
                )

            total_entities = crossref_result.get("total_entities", 0)
            documented = crossref_result.get("documented_entities", 0)
            undocumented = crossref_result.get("undocumented_entities", 0)

        except Exception as e:
            if self.verbose:
                print(f"[Hot-Path] Cross-reference analysis failed: {e}")
            entity_references = {}
            total_entities = 0
            documented = 0
            undocumented = 0

        # Layer 5: Similarity (optional, expensive)
        if include_similarity:
            if self.verbose:
                print("[Hot-Path] Running similarity analysis...")
            try:
                pipeline.analyze_similarity(
                    api_base="local",
                    token=None,
                    code_slug=str(self.adapter.repo_path),
                    code_branch=head_ref,
                    docs_slug=str(self.adapter.repo_path),
                    docs_branch=head_ref,
                    settings=self.settings
                )
            except Exception as e:
                if self.verbose:
                    print(f"[Hot-Path] Similarity analysis failed: {e}")

        elapsed = time.time() - start

        if self.verbose:
            print(f"[Hot-Path] Analysis complete in {elapsed:.1f}s")

        return HotPathAnalysis(
            changed_files=changed_files,
            files_added=semantic_result.get("files_added", 0),
            files_deleted=semantic_result.get("files_deleted", 0),
            total_entities=total_entities,
            documented_entities=documented,
            undocumented_entities=undocumented,
            entity_references=entity_references,
            communities_found=communities_found,
            changes_by_type=semantic_result.get("summary", {}),
            elapsed_seconds=elapsed
        )

    def get_change_summary(self, analysis: HotPathAnalysis) -> str:
        """
        Get human-readable summary of changes.

        Args:
            analysis: HotPathAnalysis result

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"Analyzed {len(analysis.changed_files)} files in {analysis.elapsed_seconds:.1f}s")
        lines.append("")
        lines.append("Change Classification:")
        for change_type, count in sorted(analysis.changes_by_type.items()):
            if count > 0:
                lines.append(f"  - {change_type.upper()}: {count}")

        high = len(analysis.get_high_priority_changes())
        medium = len(analysis.get_medium_priority_changes())

        lines.append("")
        lines.append("Documentation Impact:")
        lines.append(f"  - HIGH priority (MAJOR/REWRITE): {high}")
        lines.append(f"  - MEDIUM priority (MINOR): {medium}")

        lines.append("")
        lines.append("Code Entities:")
        lines.append(f"  - Total found: {analysis.total_entities}")
        lines.append(f"  - Documented: {analysis.documented_entities}")
        lines.append(f"  - Undocumented: {analysis.undocumented_entities}")

        if analysis.communities_found:
            lines.append("")
            lines.append(f"Communities: {analysis.communities_found} code clusters found")

        return "\n".join(lines)


# Convenience function for quick analysis
def analyze_pr(
    base_ref: str = "HEAD~1",
    head_ref: str = "HEAD",
    repo_path: Optional[Path] = None,
    verbose: bool = False
) -> HotPathAnalysis:
    """
    Quick function to analyze a PR or commit.

    Args:
        base_ref: Base reference (default: HEAD~1)
        head_ref: Head reference (default: HEAD)
        repo_path: Repository path (auto-detected if None)
        verbose: Enable verbose output

    Returns:
        HotPathAnalysis
    """
    analyzer = HotPathAnalyzer(repo_path, verbose)
    return analyzer.analyze_changes(base_ref, head_ref)


if __name__ == "__main__":
    """Test the integration"""
    print("Testing Hot-Path Integration")
    print("=" * 80)

    result = analyze_pr(verbose=True)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    analyzer = HotPathAnalyzer()
    print(analyzer.get_change_summary(result))

    high_priority = result.get_high_priority_changes()
    if high_priority:
        print("\n" + "-" * 80)
        print("HIGH PRIORITY CHANGES:")
        print("-" * 80)
        for change in high_priority:
            print(f"\n{change.path}")
            print(f"  Type: {change.change_type.upper()}")
            print(f"  Distance: {change.normalized_distance:.2f}")
            print(f"  Language: {change.language or 'unknown'}")

            impacted = result.get_impacted_docs(change.path)
            if impacted:
                print(f"  Impacted docs: {', '.join(impacted[:3])}")

    print("\n" + "=" * 80)
