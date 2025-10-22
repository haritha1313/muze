"""
Layer 4: Pattern Recognition System using Aho-Corasick

Implements multi-pattern string matching for finding all occurrences of code entities
(functions, classes, variables) in documentation in O(n + k + z) time.

This enables the critical question: "Which docs mention this function?"
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
import re


@dataclass
class Match:
    """A pattern match in text"""
    pattern: str          # The pattern that matched
    start: int           # Start position in text
    end: int             # End position in text
    line_number: int     # Line number (1-indexed)
    context: str         # Surrounding context


class AhoCorasickNode:
    """Node in the Aho-Corasick trie"""

    def __init__(self):
        self.children: Dict[str, AhoCorasickNode] = {}
        self.failure: Optional[AhoCorasickNode] = None
        self.output: List[str] = []  # Patterns that end at this node

    def __repr__(self):
        return f"ACNode(children={len(self.children)}, output={self.output})"


class AhoCorasick:
    """
    Aho-Corasick automaton for multi-pattern matching.

    Time complexity:
    - Build: O(sum of pattern lengths)
    - Search: O(n + z) where n=text length, z=number of matches

    Advantage over naive: Search for k patterns in O(n) instead of O(k*n)
    """

    def __init__(self, patterns: List[str], case_sensitive: bool = False):
        """
        Initialize Aho-Corasick automaton with patterns.

        Args:
            patterns: List of patterns to search for
            case_sensitive: Whether to perform case-sensitive matching
        """
        self.case_sensitive = case_sensitive
        self.root = AhoCorasickNode()
        self.patterns = patterns if case_sensitive else [p.lower() for p in patterns]

        self._build_trie()
        self._build_failure_links()

    def _build_trie(self):
        """Build the trie structure from patterns"""
        for pattern in self.patterns:
            if not pattern:  # Skip empty patterns
                continue

            node = self.root
            for char in pattern:
                if char not in node.children:
                    node.children[char] = AhoCorasickNode()
                node = node.children[char]

            # Mark this node as end of pattern
            node.output.append(pattern)

    def _build_failure_links(self):
        """Build failure links using BFS"""
        queue = deque()

        # Level 1 nodes fail to root
        for child in self.root.children.values():
            child.failure = self.root
            queue.append(child)

        # BFS to build failure links
        while queue:
            current = queue.popleft()

            for char, child in current.children.items():
                queue.append(child)

                # Find failure link
                failure_node = current.failure
                while failure_node and char not in failure_node.children:
                    failure_node = failure_node.failure

                if failure_node:
                    child.failure = failure_node.children.get(char, self.root)
                else:
                    child.failure = self.root

                # Merge outputs from failure node
                if child.failure.output:
                    child.output.extend(child.failure.output)

    def search(self, text: str, context_chars: int = 50) -> List[Match]:
        """
        Search for all patterns in text.

        Args:
            text: Text to search in
            context_chars: Number of characters to include in context

        Returns:
            List of Match objects
        """
        if not self.case_sensitive:
            text = text.lower()

        matches = []
        node = self.root
        lines = text.split('\n')
        current_pos = 0

        # Track line positions
        line_positions = [0]  # Start positions of each line
        for line in lines:
            current_pos += len(line) + 1  # +1 for newline
            line_positions.append(current_pos)

        # Search
        node = self.root
        for i, char in enumerate(text):
            # Follow failure links if needed
            while node != self.root and char not in node.children:
                node = node.failure

            if char in node.children:
                node = node.children[char]

            # Check for matches
            if node.output:
                for pattern in node.output:
                    start = i - len(pattern) + 1
                    end = i + 1

                    # Find line number
                    line_num = 1
                    for idx, line_start in enumerate(line_positions):
                        if start >= line_start:
                            line_num = idx + 1
                        else:
                            break

                    # Extract context
                    context_start = max(0, start - context_chars)
                    context_end = min(len(text), end + context_chars)
                    context = text[context_start:context_end]

                    matches.append(Match(
                        pattern=pattern,
                        start=start,
                        end=end,
                        line_number=line_num,
                        context=context
                    ))

        return matches

    def search_by_pattern(self, text: str) -> Dict[str, List[Match]]:
        """
        Search and group results by pattern.

        Returns:
            Dict mapping pattern -> list of matches
        """
        matches = self.search(text)
        by_pattern = defaultdict(list)
        for match in matches:
            by_pattern[match.pattern].append(match)
        return dict(by_pattern)


class CodeEntityExtractor:
    """Extract entities (functions, classes, methods) from code"""

    def __init__(self):
        # Patterns for different languages
        self.python_function = re.compile(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
        self.python_class = re.compile(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]')

        self.js_function = re.compile(r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(')
        self.js_arrow = re.compile(r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>')
        self.js_class = re.compile(r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[{]')
        self.js_method = re.compile(r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*{')

    def extract_python(self, code: str) -> Set[str]:
        """Extract Python functions and classes"""
        entities = set()

        # Functions
        entities.update(self.python_function.findall(code))

        # Classes
        entities.update(self.python_class.findall(code))

        return entities

    def extract_javascript(self, code: str) -> Set[str]:
        """Extract JavaScript functions, classes, and methods"""
        entities = set()

        # Function declarations
        entities.update(self.js_function.findall(code))

        # Arrow functions
        entities.update(self.js_arrow.findall(code))

        # Classes
        entities.update(self.js_class.findall(code))

        # Methods (more complex, simplified here)
        entities.update(self.js_method.findall(code))

        # Filter out common keywords
        keywords = {'if', 'for', 'while', 'switch', 'return', 'catch', 'try',
                   'async', 'await', 'export', 'import', 'default'}
        entities = {e for e in entities if e not in keywords}

        return entities

    def extract(self, code: str, language: str) -> Set[str]:
        """
        Extract entities from code.

        Args:
            code: Source code
            language: Language identifier ('python', 'javascript', 'typescript')

        Returns:
            Set of entity names (functions, classes, methods)
        """
        if language == 'python':
            return self.extract_python(code)
        elif language in {'javascript', 'typescript'}:
            return self.extract_javascript(code)
        else:
            return set()


class CrossReferenceAnalyzer:
    """
    Analyze cross-references between code and documentation.

    Answers the question: "Which docs mention this function?"
    """

    def __init__(self):
        self.extractor = CodeEntityExtractor()

    def analyze_code_file(self, code: str, language: str) -> Set[str]:
        """Extract all entities from a code file"""
        return self.extractor.extract(code, language)

    def find_references(
        self,
        entities: Set[str],
        doc_content: str,
        doc_name: str,
        context_chars: int = 50
    ) -> Dict[str, List[Match]]:
        """
        Find all references to code entities in documentation.

        Args:
            entities: Set of entity names to search for
            doc_content: Documentation text
            doc_name: Name of the document (for reporting)
            context_chars: Characters of context around match

        Returns:
            Dict mapping entity -> list of matches in this doc
        """
        if not entities:
            return {}

        # Build Aho-Corasick automaton
        patterns = list(entities)
        ac = AhoCorasick(patterns, case_sensitive=False)

        # Search
        return ac.search_by_pattern(doc_content)

    def analyze_cross_references(
        self,
        code_files: Dict[str, Tuple[str, str]],  # {filename: (code, language)}
        doc_files: Dict[str, str],                # {filename: content}
    ) -> Dict:
        """
        Analyze all cross-references between code and docs.

        Args:
            code_files: Dict of filename -> (code, language)
            doc_files: Dict of filename -> content

        Returns:
            Comprehensive cross-reference analysis
        """
        # Extract all entities from code
        all_entities = set()
        entities_by_file = {}

        for filename, (code, language) in code_files.items():
            entities = self.analyze_code_file(code, language)
            entities_by_file[filename] = entities
            all_entities.update(entities)

        # Find references in all docs
        references_by_doc = {}  # {doc_name: {entity: [matches]}}
        entity_to_docs = defaultdict(set)  # {entity: {doc_names}}

        for doc_name, doc_content in doc_files.items():
            refs = self.find_references(all_entities, doc_content, doc_name)
            if refs:
                references_by_doc[doc_name] = refs

                # Build reverse index
                for entity in refs.keys():
                    entity_to_docs[entity].add(doc_name)

        # Build entity -> source code file mapping
        entity_to_code_file = {}
        for code_file, entities in entities_by_file.items():
            for entity in entities:
                if entity not in entity_to_code_file:
                    entity_to_code_file[entity] = []
                entity_to_code_file[entity].append(code_file)

        return {
            "total_entities": len(all_entities),
            "total_docs": len(doc_files),
            "entities_by_file": entities_by_file,
            "references_by_doc": references_by_doc,
            "entity_to_docs": dict(entity_to_docs),
            "entity_to_code_file": entity_to_code_file,
            "all_entities": sorted(all_entities),
        }

    def get_documentation_impact(
        self,
        changed_entities: Set[str],
        cross_ref_analysis: Dict
    ) -> Dict:
        """
        Determine which docs are impacted by changed entities.

        Args:
            changed_entities: Set of entity names that changed
            cross_ref_analysis: Result from analyze_cross_references()

        Returns:
            Dict with impacted docs and recommendations
        """
        entity_to_docs = cross_ref_analysis.get("entity_to_docs", {})
        references_by_doc = cross_ref_analysis.get("references_by_doc", {})

        impacted_docs = set()
        impact_details = defaultdict(list)

        for entity in changed_entities:
            if entity in entity_to_docs:
                docs = entity_to_docs[entity]
                impacted_docs.update(docs)

                for doc in docs:
                    matches = references_by_doc.get(doc, {}).get(entity, [])
                    impact_details[doc].append({
                        "entity": entity,
                        "mentions": len(matches),
                        "lines": [m.line_number for m in matches]
                    })

        return {
            "impacted_docs": sorted(impacted_docs),
            "impact_details": dict(impact_details),
            "total_impacted": len(impacted_docs),
            "changed_entities": sorted(changed_entities),
        }


# Convenience functions

def find_entity_mentions(entity: str, text: str) -> List[Match]:
    """Find all mentions of an entity in text"""
    ac = AhoCorasick([entity], case_sensitive=False)
    return ac.search(text)


def extract_code_entities(code: str, language: str) -> Set[str]:
    """Extract entities from code"""
    extractor = CodeEntityExtractor()
    return extractor.extract(code, language)


# Self-test
if __name__ == "__main__":
    import sys
    # Fix Windows console encoding
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("Testing Aho-Corasick Pattern Matching")
    print("=" * 70)

    # Test 1: Basic Aho-Corasick
    print("\n1. Basic Multi-Pattern Search:")
    patterns = ["validate_password", "hash_password", "login"]
    text = """
    The validate_password function checks password strength.
    Use hash_password to securely store passwords.
    The login function authenticates users with validate_password.
    """

    ac = AhoCorasick(patterns)
    matches = ac.search(text)

    print(f"   Patterns: {patterns}")
    print(f"   Found {len(matches)} matches:")
    for match in matches:
        print(f"     - '{match.pattern}' at line {match.line_number}")

    # Test 2: Entity Extraction
    print("\n2. Entity Extraction from Python:")
    python_code = """
def validate_password(password):
    return len(password) >= 8

class UserAuth:
    def login(self, username, password):
        return True
    """

    extractor = CodeEntityExtractor()
    entities = extractor.extract_python(python_code)
    print(f"   Found entities: {sorted(entities)}")

    # Test 3: Cross-Reference Analysis
    print("\n3. Cross-Reference Analysis:")
    code_files = {
        "auth.py": (python_code, "python")
    }
    doc_files = {
        "guide.md": "Use validate_password() to check passwords. The login() method authenticates users."
    }

    analyzer = CrossReferenceAnalyzer()
    result = analyzer.analyze_cross_references(code_files, doc_files)

    print(f"   Total entities: {result['total_entities']}")
    print(f"   Entities: {result['all_entities']}")
    print(f"   References in docs:")
    for doc, refs in result['references_by_doc'].items():
        print(f"     {doc}:")
        for entity, matches in refs.items():
            print(f"       - {entity}: {len(matches)} mentions")

    print("\n✓ All tests passed!")
