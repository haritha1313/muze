"""
Component 1: Documentation Impact Analyzer

Orchestrates all 5 Hot-Path layers to analyze code changes and identify
which documentation needs updating, with priority scoring.

Usage:
    from doc_analyzer import DocumentationAnalyzer

    analyzer = DocumentationAnalyzer(code_slug, docs_slug, api_token)
    result = analyzer.analyze_changes(old_ref, new_ref)
    priorities = analyzer.prioritize_documentation(result)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import time

# Import existing layer implementations
import pipeline
import semantic
import pattern_matching


class Priority(Enum):
    """Documentation update priority levels"""
    HIGH = "high"       # Score > 5: MAJOR/REWRITE changes with multiple mentions
    MEDIUM = "medium"   # Score 2-5: MINOR changes with mentions, or MAJOR with few mentions
    LOW = "low"         # Score < 2: Single mentions or undocumented code


@dataclass
class ChangedFile:
    """Information about a changed code file"""
    path: str
    change_type: str  # "identical", "refactor", "minor", "major", "rewrite"
    distance: float
    normalized_distance: float
    size_old: int
    size_new: int
    needs_doc_update: bool
    language: Optional[str] = None
    entities: Set[str] = field(default_factory=set)


@dataclass
class ImpactedDoc:
    """Information about a documentation file that needs updating"""
    doc_path: str
    priority: Priority
    score: float
    reasons: List[str]
    changed_entities: List[str]
    mention_counts: Dict[str, int]
    line_numbers: Dict[str, List[int]]
    community_size: int = 0


@dataclass
class AnalysisResult:
    """Complete analysis result from all 5 layers"""
    # Layer 1: Changed files
    changed_files: List[ChangedFile]
    files_added: List[str]
    files_deleted: List[str]

    # Layer 2: Semantic analysis
    semantic_changes: Dict[str, Dict]  # file -> change info

    # Layer 3: Communities
    communities: List[List[str]]
    community_map: Dict[str, int]  # entity -> community index

    # Layer 4: Cross-references
    cross_refs: Dict[str, List[str]]  # entity -> list of docs
    references_by_doc: Dict[str, Dict[str, List]]  # doc -> {entity: [matches]}
    all_entities: Set[str]

    # Layer 5: Similarity
    similar_pairs: List[Tuple[str, str, float]]

    # Metadata
    old_ref: str
    new_ref: str
    elapsed_seconds: float

    # Computed
    impacted_docs: List[ImpactedDoc] = field(default_factory=list)


class DocumentationAnalyzer:
    """
    Orchestrates all 5 layers to analyze code changes and identify documentation impact.

    Layers:
        1. Merkle Tree - Detect changed files
        2. Semantic Analysis - Classify change severity
        3. Communities - Find related code clusters
        4. Cross-References - Map code entities to docs
        5. Similarity - Find similar code patterns
    """

    def __init__(
        self,
        code_slug: Optional[str] = None,
        docs_slug: Optional[str] = None,
        api_token: Optional[str] = None,
        api_base: str = "https://api.github.com",
        settings: Optional[pipeline.PipelineSettings] = None
    ):
        """
        Initialize analyzer.

        Args:
            code_slug: GitHub repository slug (owner/repo)
            docs_slug: Documentation repository slug (can be same as code_slug)
            api_token: GitHub API token
            api_base: GitHub API base URL
            settings: Pipeline settings (uses defaults if None)
        """
        self.code_slug = code_slug
        self.docs_slug = docs_slug or code_slug  # Default to same repo
        self.api_token = api_token
        self.api_base = api_base
        self.settings = settings or pipeline.PipelineSettings()

        # Cache for analysis results
        self._cache: Dict[str, AnalysisResult] = {}

    def analyze_changes(
        self,
        old_ref: str,
        new_ref: str,
        code_branch: Optional[str] = None,
        docs_branch: Optional[str] = None
    ) -> AnalysisResult:
        """
        Run complete analysis pipeline on code changes.

        Args:
            old_ref: Old version reference (branch name or commit SHA)
            new_ref: New version reference (branch name or commit SHA)
            code_branch: Optional branch for additional context
            docs_branch: Optional docs branch

        Returns:
            AnalysisResult with findings from all 5 layers
        """
        start_time = time.time()

        print(f"Starting analysis: {old_ref} -> {new_ref}")

        # Layer 2: Semantic Analysis (most important for doc updates)
        print("\n[Layer 2] Running semantic analysis...")
        semantic_result = pipeline.analyze_semantic_diff(
            self.api_base,
            self.api_token,
            self.code_slug,
            old_ref,
            new_ref,
            self.settings
        )

        # Convert to ChangedFile objects
        changed_files = []
        semantic_changes = {}

        for change in semantic_result.get("changes", []):
            cf = ChangedFile(
                path=change["path"],
                change_type=change["change_type"],
                distance=change["distance"],
                normalized_distance=change["normalized_distance"],
                size_old=change["size_old"],
                size_new=change["size_new"],
                needs_doc_update=change["needs_doc_update"],
                language=change.get("language")
            )
            changed_files.append(cf)
            semantic_changes[cf.path] = change

        files_added = []
        for i in range(semantic_result.get("files_added", 0)):
            files_added.append(f"<new_file_{i}>")

        files_deleted = []
        for i in range(semantic_result.get("files_deleted", 0)):
            files_deleted.append(f"<deleted_file_{i}>")

        # Layer 3: Communities (understand code structure)
        print("[Layer 3] Analyzing communities...")
        try:
            community_result = pipeline.analyze_communities(
                self.api_base,
                self.api_token,
                self.code_slug,
                new_ref,  # Use new version for current structure
                self.settings
            )
            communities = community_result.get("communities", [])
        except Exception as e:
            print(f"Warning: Community analysis failed: {e}")
            communities = []

        # Build community map
        community_map = {}
        for idx, community_members in enumerate(communities):
            for member in community_members:
                community_map[member] = idx

        # Layer 4: Cross-References (map entities to docs)
        print("[Layer 4] Analyzing cross-references...")
        crossref_result = pipeline.analyze_cross_references(
            self.api_base,
            self.api_token,
            self.code_slug,
            new_ref,  # Use new version
            self.docs_slug,
            docs_branch or new_ref,
            self.settings
        )

        cross_refs = crossref_result.get("entity_to_docs", {})
        references_by_doc = crossref_result.get("cross_reference_details", {}).get("references_by_doc", {})
        all_entities = set(crossref_result.get("all_entities", []))

        # Extract entities from changed files
        for cf in changed_files:
            # Extract entity names from file path
            # Simple heuristic: functions/classes are often in top_documented entities
            for entity in cross_refs.keys():
                # If entity is likely from this file (heuristic)
                if entity.lower() in cf.path.lower() or cf.path.split('/')[-1].replace('.py', '').replace('.js', '') in entity.lower():
                    cf.entities.add(entity)

        # Layer 5: Similarity (find related patterns)
        print("[Layer 5] Analyzing similarity...")
        try:
            similarity_result = pipeline.analyze_similarity(
                self.api_base,
                self.api_token,
                self.code_slug,
                new_ref,
                self.docs_slug,
                docs_branch or new_ref,
                self.settings
            )
            similar_pairs = similarity_result.get("top_pairs", [])
        except Exception as e:
            print(f"Warning: Similarity analysis failed: {e}")
            similar_pairs = []

        elapsed = time.time() - start_time

        result = AnalysisResult(
            changed_files=changed_files,
            files_added=files_added,
            files_deleted=files_deleted,
            semantic_changes=semantic_changes,
            communities=communities,
            community_map=community_map,
            cross_refs=cross_refs,
            references_by_doc=references_by_doc,
            all_entities=all_entities,
            similar_pairs=similar_pairs,
            old_ref=old_ref,
            new_ref=new_ref,
            elapsed_seconds=elapsed
        )

        print(f"\n✓ Analysis complete in {elapsed:.1f}s")
        print(f"  - {len(changed_files)} files changed")
        print(f"  - {len(communities)} communities found")
        print(f"  - {len(cross_refs)} entities documented")

        return result

    def prioritize_documentation(self, analysis: AnalysisResult) -> List[ImpactedDoc]:
        """
        Prioritize which documentation needs updating based on analysis results.

        Scoring formula:
            Score = (change_severity × 2) + (mention_count × 1.5) + (community_size × 0.5)

        Priority levels:
            - HIGH (score > 5): MAJOR/REWRITE with 3+ mentions, or large community impact
            - MEDIUM (score 2-5): MINOR with multiple mentions, or MAJOR with 1-2 mentions
            - LOW (score < 2): Single mentions or undocumented code

        Args:
            analysis: AnalysisResult from analyze_changes()

        Returns:
            Sorted list of ImpactedDoc objects (highest priority first)
        """
        print("\n[Prioritization] Scoring documentation updates...")

        # Map change types to severity scores
        severity_scores = {
            "identical": 0,
            "refactor": 0,   # No doc update needed
            "minor": 1,
            "major": 3,
            "rewrite": 5
        }

        # Track which docs are impacted by which entities
        doc_impacts: Dict[str, Dict] = {}

        for cf in analysis.changed_files:
            # Skip refactors and identical
            if not cf.needs_doc_update:
                continue

            severity = severity_scores.get(cf.change_type, 1)

            # Find which entities are in this file
            entities_in_file = set()

            # Method 1: Use entities already associated with changed file
            entities_in_file.update(cf.entities)

            # Method 2: Check if any documented entity matches file name
            file_basename = cf.path.split('/')[-1].replace('.py', '').replace('.js', '').replace('.ts', '')
            for entity in analysis.all_entities:
                if file_basename.lower() in entity.lower() or entity.lower() in file_basename.lower():
                    entities_in_file.add(entity)

            # Find which docs mention these entities
            for entity in entities_in_file:
                if entity in analysis.cross_refs:
                    for doc_path in analysis.cross_refs[entity]:
                        # Initialize doc impact tracking
                        if doc_path not in doc_impacts:
                            doc_impacts[doc_path] = {
                                "entities": set(),
                                "severity_sum": 0,
                                "mention_counts": {},
                                "line_numbers": {},
                                "reasons": []
                            }

                        # Get mention count for this entity in this doc
                        mention_count = len(
                            analysis.references_by_doc.get(doc_path, {}).get(entity, [])
                        )

                        # Get line numbers
                        line_nums = []
                        if doc_path in analysis.references_by_doc:
                            if entity in analysis.references_by_doc[doc_path]:
                                # References_by_doc has {entity: match_count}
                                # We'll approximate line numbers
                                line_nums = list(range(1, mention_count + 1))

                        doc_impacts[doc_path]["entities"].add(entity)
                        doc_impacts[doc_path]["severity_sum"] += severity
                        doc_impacts[doc_path]["mention_counts"][entity] = mention_count
                        doc_impacts[doc_path]["line_numbers"][entity] = line_nums
                        doc_impacts[doc_path]["reasons"].append(
                            f"{entity}: {cf.change_type.upper()} change (distance: {cf.normalized_distance:.2f})"
                        )

        # Compute scores and create ImpactedDoc objects
        impacted_docs = []

        for doc_path, impact_data in doc_impacts.items():
            entities = list(impact_data["entities"])

            # Calculate community size (max community size of all entities)
            community_size = 0
            for entity in entities:
                if entity in analysis.community_map:
                    comm_idx = analysis.community_map[entity]
                    if comm_idx < len(analysis.communities):
                        community_size = max(community_size, len(analysis.communities[comm_idx]))

            # Calculate average severity
            avg_severity = impact_data["severity_sum"] / max(len(entities), 1)

            # Calculate total mentions
            total_mentions = sum(impact_data["mention_counts"].values())

            # Scoring formula
            score = (avg_severity * 2) + (total_mentions * 1.5) + (community_size * 0.5)

            # Determine priority
            if score > 5:
                priority = Priority.HIGH
            elif score >= 2:
                priority = Priority.MEDIUM
            else:
                priority = Priority.LOW

            impacted_doc = ImpactedDoc(
                doc_path=doc_path,
                priority=priority,
                score=score,
                reasons=impact_data["reasons"],
                changed_entities=entities,
                mention_counts=impact_data["mention_counts"],
                line_numbers=impact_data["line_numbers"],
                community_size=community_size
            )

            impacted_docs.append(impacted_doc)

        # Sort by score (highest first)
        impacted_docs.sort(key=lambda d: d.score, reverse=True)

        # Store in analysis result
        analysis.impacted_docs = impacted_docs

        # Print summary
        print(f"\n✓ Prioritization complete:")
        high = sum(1 for d in impacted_docs if d.priority == Priority.HIGH)
        medium = sum(1 for d in impacted_docs if d.priority == Priority.MEDIUM)
        low = sum(1 for d in impacted_docs if d.priority == Priority.LOW)

        print(f"  - {high} HIGH priority docs")
        print(f"  - {medium} MEDIUM priority docs")
        print(f"  - {low} LOW priority docs")

        return impacted_docs

    def get_change_summary(self, analysis: AnalysisResult) -> Dict:
        """
        Get a human-readable summary of changes.

        Args:
            analysis: AnalysisResult from analyze_changes()

        Returns:
            Dict with summary statistics
        """
        change_type_counts = {}
        for cf in analysis.changed_files:
            change_type_counts[cf.change_type] = change_type_counts.get(cf.change_type, 0) + 1

        needs_update = sum(1 for cf in analysis.changed_files if cf.needs_doc_update)

        priority_counts = {
            "high": sum(1 for d in analysis.impacted_docs if d.priority == Priority.HIGH),
            "medium": sum(1 for d in analysis.impacted_docs if d.priority == Priority.MEDIUM),
            "low": sum(1 for d in analysis.impacted_docs if d.priority == Priority.LOW),
        }

        return {
            "total_files_changed": len(analysis.changed_files),
            "files_added": len(analysis.files_added),
            "files_deleted": len(analysis.files_deleted),
            "change_types": change_type_counts,
            "files_needing_doc_update": needs_update,
            "impacted_docs_total": len(analysis.impacted_docs),
            "priority_breakdown": priority_counts,
            "communities_found": len(analysis.communities),
            "documented_entities": len(analysis.cross_refs),
            "similar_pairs": len(analysis.similar_pairs),
            "analysis_time": f"{analysis.elapsed_seconds:.1f}s"
        }


# Convenience functions

def analyze_github_repo(
    code_slug: str,
    old_ref: str,
    new_ref: str,
    docs_slug: Optional[str] = None,
    api_token: Optional[str] = None
) -> Tuple[AnalysisResult, List[ImpactedDoc]]:
    """
    Convenience function to analyze a GitHub repository.

    Args:
        code_slug: Repository slug (owner/repo)
        old_ref: Old version (branch or SHA)
        new_ref: New version (branch or SHA)
        docs_slug: Documentation repo (defaults to same as code)
        api_token: GitHub API token

    Returns:
        (AnalysisResult, List of ImpactedDoc)
    """
    analyzer = DocumentationAnalyzer(code_slug, docs_slug, api_token)
    result = analyzer.analyze_changes(old_ref, new_ref)
    priorities = analyzer.prioritize_documentation(result)
    return result, priorities


# Self-test
if __name__ == "__main__":
    print("DocumentationAnalyzer - Component 1")
    print("=" * 80)
    print("\nThis module orchestrates all 5 Hot-Path layers to analyze")
    print("code changes and determine which documentation needs updating.")
    print("\nUsage:")
    print("  from doc_analyzer import DocumentationAnalyzer")
    print("  ")
    print("  analyzer = DocumentationAnalyzer('owner/repo', api_token='...')")
    print("  result = analyzer.analyze_changes('v1.0', 'v2.0')")
    print("  priorities = analyzer.prioritize_documentation(result)")
    print("\nFor full examples, see end-to-end.md")
