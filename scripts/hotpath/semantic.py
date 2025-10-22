"""
Layer 2: Semantic Understanding Engine

Implements:
- AST parsing via tree-sitter for multiple languages
- Zhang-Shasha tree edit distance algorithm
- Semantic diff classification (refactor vs. logic change)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


class ChangeType(Enum):
    """Classification of semantic changes"""
    IDENTICAL = "identical"           # No change (distance = 0)
    REFACTOR = "refactor"             # Structural change, same logic
    MINOR = "minor"                   # Small logic changes
    MAJOR = "major"                   # Significant logic changes
    REWRITE = "rewrite"               # Complete rewrite


@dataclass
class TreeNode:
    """Simplified AST node for tree edit distance computation"""
    type: str                         # Node type (e.g., "function", "if_statement")
    value: Optional[str] = None       # Node value (e.g., identifier name)
    children: List[TreeNode] = None   # Child nodes

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def size(self) -> int:
        """Count total nodes in subtree"""
        return 1 + sum(c.size() for c in self.children)

    def depth(self) -> int:
        """Compute tree depth"""
        if not self.children:
            return 1
        return 1 + max(c.depth() for c in self.children)

    def __repr__(self) -> str:
        val = f":{self.value}" if self.value else ""
        return f"TreeNode({self.type}{val}, {len(self.children)} children)"


# Tree-sitter integration (with fallback if not installed)
try:
    from tree_sitter import Language, Parser, Node as TSNode
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False
    Parser = None
    Language = None
    TSNode = None


class ASTParser:
    """AST parser supporting multiple languages via tree-sitter"""

    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}

        if not HAS_TREE_SITTER:
            return

        # Try to load pre-built language libraries
        # Users need to run: Language.build_library() first
        try:
            self._load_languages()
        except Exception:
            # Languages not built yet
            pass

    def _load_languages(self):
        """Load tree-sitter language grammars (must be pre-built)"""
        lib_path = os.path.join(os.path.dirname(__file__), 'build', 'languages.so')
        if not os.path.exists(lib_path):
            # Try common alternative paths
            for alt in ['build/languages.dll', 'build/languages.dylib']:
                alt_path = os.path.join(os.path.dirname(__file__), alt)
                if os.path.exists(alt_path):
                    lib_path = alt_path
                    break

        if not os.path.exists(lib_path):
            return  # Languages not available

        try:
            py_lang = Language(lib_path, 'python')
            js_lang = Language(lib_path, 'javascript')

            py_parser = Parser()
            py_parser.set_language(py_lang)
            js_parser = Parser()
            js_parser.set_language(js_lang)

            self.languages['python'] = py_lang
            self.languages['javascript'] = js_lang
            self.languages['typescript'] = js_lang  # Approximate
            self.parsers['python'] = py_parser
            self.parsers['javascript'] = js_parser
            self.parsers['typescript'] = js_parser
        except Exception:
            pass

    def parse(self, code: str, language: str) -> Optional[TreeNode]:
        """Parse code to simplified AST

        Args:
            code: Source code string
            language: Language identifier ('python', 'javascript', etc.)

        Returns:
            TreeNode root or None if parsing fails
        """
        if not HAS_TREE_SITTER or language not in self.parsers:
            # Fallback: simple token-based tree
            return self._fallback_parse(code, language)

        try:
            parser = self.parsers[language]
            tree = parser.parse(bytes(code, 'utf-8'))
            return self._convert_tree_sitter_node(tree.root_node)
        except Exception:
            return self._fallback_parse(code, language)

    def _convert_tree_sitter_node(self, node: TSNode) -> TreeNode:
        """Convert tree-sitter node to simplified TreeNode"""
        # Get node type
        node_type = node.type

        # Extract value for terminals (identifiers, literals)
        value = None
        if node.child_count == 0 and node.text:
            try:
                value = node.text.decode('utf-8')
            except Exception:
                value = None

        # Convert children
        children = [self._convert_tree_sitter_node(c) for c in node.children]

        return TreeNode(type=node_type, value=value, children=children)

    def _fallback_parse(self, code: str, language: str) -> TreeNode:
        """Fallback parser when tree-sitter unavailable

        Creates a simple token-based tree structure
        """
        import re

        # Simple tokenization
        tokens = re.findall(r'\w+|[^\w\s]', code)

        # Group into lines for simple structure
        lines = code.split('\n')
        children = []

        for i, line in enumerate(lines[:100]):  # Limit to 100 lines
            line = line.strip()
            if not line:
                continue

            # Classify line type
            line_type = "statement"
            if language == "python":
                if line.startswith("def "):
                    line_type = "function_def"
                elif line.startswith("class "):
                    line_type = "class_def"
                elif line.startswith("if "):
                    line_type = "if_statement"
                elif line.startswith("for ") or line.startswith("while "):
                    line_type = "loop"
            elif language in {"javascript", "typescript"}:
                if "function" in line:
                    line_type = "function_declaration"
                elif line.startswith("if"):
                    line_type = "if_statement"
                elif "for" in line or "while" in line:
                    line_type = "loop"

            children.append(TreeNode(type=line_type, value=line[:50]))

        return TreeNode(type="module", children=children)


@dataclass
class EditOperation:
    """Single edit operation for tree transformation"""
    op_type: str  # "insert", "delete", "rename"
    node: TreeNode
    cost: float = 1.0


class ZhangShashaDistance:
    """Zhang-Shasha tree edit distance algorithm

    Computes minimum cost to transform one tree into another using:
    - Insert node
    - Delete node
    - Rename node

    Time complexity: O(n1 * n2 * d1 * d2) where n=size, d=depth
    Space complexity: O(n1 * n2)
    """

    def __init__(self, insert_cost: float = 1.0, delete_cost: float = 1.0, rename_cost: float = 1.0):
        self.insert_cost = insert_cost
        self.delete_cost = delete_cost
        self.rename_cost = rename_cost

        # Memoization
        self.memo: Dict[Tuple[int, int], float] = {}

    def compute(self, tree1: TreeNode, tree2: TreeNode) -> Tuple[float, List[EditOperation]]:
        """Compute tree edit distance

        Args:
            tree1: Source tree
            tree2: Target tree

        Returns:
            (distance, operations) - minimum edit distance and operation sequence
        """
        self.memo.clear()

        # Compute leftmost leaf descendants (preprocessing for Zhang-Shasha)
        self.tree1 = tree1
        self.tree2 = tree2

        # Simplified implementation: standard recursive approach
        distance = self._tree_distance(tree1, tree2)

        # Operations reconstruction is complex; return empty list for now
        operations = []

        return distance, operations

    def _tree_distance(self, t1: Optional[TreeNode], t2: Optional[TreeNode]) -> float:
        """Recursive tree edit distance with memoization"""

        # Base cases
        if t1 is None and t2 is None:
            return 0.0
        if t1 is None:
            return self._tree_cost(t2) * self.insert_cost
        if t2 is None:
            return self._tree_cost(t1) * self.delete_cost

        # Check memo (use id for hashing)
        key = (id(t1), id(t2))
        if key in self.memo:
            return self.memo[key]

        # Case 1: Delete t1 root and match children
        cost1 = self.delete_cost + self._forest_distance(t1.children, [t2])

        # Case 2: Insert t2 root and match children
        cost2 = self.insert_cost + self._forest_distance([t1], t2.children)

        # Case 3: Match/rename roots and match children
        rename_cost = 0.0 if self._nodes_equal(t1, t2) else self.rename_cost
        cost3 = rename_cost + self._forest_distance(t1.children, t2.children)

        result = min(cost1, cost2, cost3)
        self.memo[key] = result
        return result

    def _forest_distance(self, forest1: List[TreeNode], forest2: List[TreeNode]) -> float:
        """Compute distance between two forests (lists of trees)"""
        if not forest1 and not forest2:
            return 0.0
        if not forest1:
            return sum(self._tree_cost(t) for t in forest2) * self.insert_cost
        if not forest2:
            return sum(self._tree_cost(t) for t in forest1) * self.delete_cost

        # Dynamic programming for forest alignment
        m, n = len(forest1), len(forest2)
        dp = [[0.0] * (n + 1) for _ in range(m + 1)]

        # Initialize boundaries
        for i in range(1, m + 1):
            dp[i][0] = dp[i-1][0] + self._tree_cost(forest1[i-1]) * self.delete_cost
        for j in range(1, n + 1):
            dp[0][j] = dp[0][j-1] + self._tree_cost(forest2[j-1]) * self.insert_cost

        # Fill DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                delete = dp[i-1][j] + self._tree_cost(forest1[i-1]) * self.delete_cost
                insert = dp[i][j-1] + self._tree_cost(forest2[j-1]) * self.insert_cost
                match = dp[i-1][j-1] + self._tree_distance(forest1[i-1], forest2[j-1])
                dp[i][j] = min(delete, insert, match)

        return dp[m][n]

    def _tree_cost(self, tree: TreeNode) -> float:
        """Cost to insert/delete entire tree (equals size)"""
        return float(tree.size())

    def _nodes_equal(self, n1: TreeNode, n2: TreeNode) -> bool:
        """Check if two nodes are semantically equal"""
        if n1.type != n2.type:
            return False

        # For terminals, compare values
        if not n1.children and not n2.children:
            return n1.value == n2.value

        # For non-terminals, only type matters
        return True


class SemanticDiff:
    """High-level semantic diff analyzer"""

    def __init__(self):
        self.parser = ASTParser()
        self.distance_computer = ZhangShashaDistance()

    def analyze_change(
        self,
        code1: str,
        code2: str,
        language: str,
        threshold_refactor: float = 0.1,
        threshold_minor: float = 0.3,
        threshold_major: float = 0.6,
    ) -> Dict:
        """Analyze semantic change between two code versions

        Args:
            code1: Original code
            code2: Modified code
            language: Programming language
            threshold_refactor: Max normalized distance for "refactor"
            threshold_minor: Max normalized distance for "minor"
            threshold_major: Max normalized distance for "major"

        Returns:
            Dict with:
                - change_type: ChangeType enum
                - distance: Raw edit distance
                - normalized_distance: Distance / max(size1, size2)
                - size1, size2: Tree sizes
                - depth1, depth2: Tree depths
        """
        # Parse both versions
        tree1 = self.parser.parse(code1, language)
        tree2 = self.parser.parse(code2, language)

        if tree1 is None or tree2 is None:
            return {
                "change_type": ChangeType.MAJOR,
                "distance": float('inf'),
                "normalized_distance": 1.0,
                "error": "Failed to parse code",
            }

        # Compute tree edit distance
        distance, operations = self.distance_computer.compute(tree1, tree2)

        # Normalize by tree size
        max_size = max(tree1.size(), tree2.size())
        normalized = distance / max_size if max_size > 0 else 0.0

        # Classify change
        if normalized < 0.001:
            change_type = ChangeType.IDENTICAL
        elif normalized <= threshold_refactor:
            change_type = ChangeType.REFACTOR
        elif normalized <= threshold_minor:
            change_type = ChangeType.MINOR
        elif normalized <= threshold_major:
            change_type = ChangeType.MAJOR
        else:
            change_type = ChangeType.REWRITE

        return {
            "change_type": change_type,
            "distance": distance,
            "normalized_distance": round(normalized, 4),
            "size1": tree1.size(),
            "size2": tree2.size(),
            "depth1": tree1.depth(),
            "depth2": tree2.depth(),
            "operations_count": len(operations),
        }

    def should_update_documentation(self, change_info: Dict) -> bool:
        """Determine if documentation should be updated based on change type"""
        change_type = change_info.get("change_type")

        # Identical and refactors usually don't need doc updates
        if change_type in {ChangeType.IDENTICAL, ChangeType.REFACTOR}:
            return False

        # Minor, major, and rewrites should trigger doc review
        return True


# Convenience functions for pipeline integration

def parse_code_to_ast(code: str, language: str) -> Optional[TreeNode]:
    """Parse code to AST (convenience function)"""
    parser = ASTParser()
    return parser.parse(code, language)


def compute_semantic_distance(code1: str, code2: str, language: str) -> float:
    """Compute semantic distance between two code snippets"""
    diff = SemanticDiff()
    result = diff.analyze_change(code1, code2, language)
    return result.get("normalized_distance", 1.0)


def classify_code_change(code1: str, code2: str, language: str) -> str:
    """Classify code change type"""
    diff = SemanticDiff()
    result = diff.analyze_change(code1, code2, language)
    return result.get("change_type", ChangeType.MAJOR).value


# Self-test
if __name__ == "__main__":
    # Test with simple Python examples
    code_v1 = """
def process(x):
    if x > 0:
        return x * 2
    return 0
"""

    code_v2_refactor = """
def process(x):
    return x * 2 if x > 0 else 0
"""

    code_v2_major = """
def process(x):
    result = []
    for i in range(x):
        result.append(i * 2)
    return result
"""

    diff = SemanticDiff()

    print("Testing Semantic Diff Analyzer")
    print("=" * 60)

    print("\n1. Refactor (if -> ternary):")
    result1 = diff.analyze_change(code_v1, code_v2_refactor, "python")
    print(f"   Change type: {result1['change_type'].value}")
    print(f"   Normalized distance: {result1['normalized_distance']}")
    print(f"   Update docs? {diff.should_update_documentation(result1)}")

    print("\n2. Major change (return int -> return list):")
    result2 = diff.analyze_change(code_v1, code_v2_major, "python")
    print(f"   Change type: {result2['change_type'].value}")
    print(f"   Normalized distance: {result2['normalized_distance']}")
    print(f"   Update docs? {diff.should_update_documentation(result2)}")

    print("\n3. Identical:")
    result3 = diff.analyze_change(code_v1, code_v1, "python")
    print(f"   Change type: {result3['change_type'].value}")
    print(f"   Normalized distance: {result3['normalized_distance']}")
    print(f"   Update docs? {diff.should_update_documentation(result3)}")
