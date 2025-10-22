"""
Component 2: LLM Documentation Generator

Uses LLM to generate documentation updates based on code changes.
Supports multiple providers: OpenAI, Anthropic (Claude), and local models.

Usage:
    from llm_doc_generator import LLMDocGenerator

    generator = LLMDocGenerator(provider="openai", api_key="...")
    suggestion = generator.generate_doc_update(
        old_code=old_code,
        new_code=new_code,
        current_doc=current_doc,
        change_type="major",
        entity_name="validate_password",
        context={"mentions": 4, "file": "auth.py"}
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import os
import json
import time


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class DocSuggestion:
    """Documentation update suggestion from LLM"""
    updated_doc: str           # Suggested new documentation
    diff: str                  # Markdown diff showing changes
    explanation: str           # What changed and why
    confidence: float          # 0-1 confidence score
    provider: str              # Which LLM was used
    model: str                 # Specific model name
    tokens_used: int = 0       # Tokens consumed
    cost_usd: float = 0.0      # Estimated cost
    generation_time: float = 0.0  # Time taken


class LLMDocGenerator:
    """
    Uses LLM to generate documentation updates based on code changes.

    Supports multiple providers with automatic fallback:
    1. OpenAI GPT-4 (best quality)
    2. Anthropic Claude (great at technical docs)
    3. Local models (for privacy/cost)
    """

    # Cost per 1K tokens (approximate, as of 2024)
    COSTS = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "local": {"input": 0, "output": 0},
    }

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        """
        Initialize LLM documentation generator.

        Args:
            provider: "openai", "anthropic", or "local"
            api_key: API key for the provider (or None to use env vars)
            model: Specific model to use (uses provider default if None)
            temperature: LLM temperature (0.0-1.0, lower is more deterministic)
            max_tokens: Maximum tokens to generate
        """
        self.provider = LLMProvider(provider)
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        elif provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
        elif provider == "anthropic":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        else:
            self.api_key = None

        # Set default model
        if model:
            self.model = model
        elif self.provider == LLMProvider.OPENAI:
            self.model = "gpt-4-turbo"
        elif self.provider == LLMProvider.ANTHROPIC:
            self.model = "claude-3-5-sonnet-20241022"
        else:
            self.model = "local-model"

        # Initialize client
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the LLM client"""
        if self.provider == LLMProvider.OPENAI:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                print("Warning: openai package not installed. Install with: pip install openai")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")

        elif self.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                print("Warning: anthropic package not installed. Install with: pip install anthropic")
            except Exception as e:
                print(f"Warning: Failed to initialize Anthropic client: {e}")

    def generate_doc_update(
        self,
        old_code: str,
        new_code: str,
        current_doc: str,
        change_type: str,
        entity_name: str,
        context: Dict,
        filename: Optional[str] = None,
        language: Optional[str] = None
    ) -> DocSuggestion:
        """
        Generate documentation update suggestion.

        Args:
            old_code: Previous version of the code
            new_code: New version of the code
            current_doc: Current documentation content
            change_type: "major", "minor", or "rewrite"
            entity_name: Name of changed function/class
            context: Additional context dict with keys:
                - mentions: Number of times mentioned in docs
                - distance: Semantic distance
                - line_numbers: List of line numbers where mentioned
                - community: Community this belongs to
            filename: Source file name (optional)
            language: Programming language (optional)

        Returns:
            DocSuggestion with updated documentation
        """
        start_time = time.time()

        # Build the prompt
        prompt = self._build_prompt(
            old_code, new_code, current_doc, change_type,
            entity_name, context, filename, language
        )

        # Call LLM
        if self.client is None:
            return self._fallback_suggestion(
                current_doc, change_type, entity_name, context
            )

        try:
            response_text, tokens_used = self._call_llm(prompt)

            # Parse response
            updated_doc, explanation, confidence = self._parse_response(
                response_text, current_doc
            )

            # Generate diff
            diff = self._generate_diff(current_doc, updated_doc)

            # Calculate cost
            cost = self._calculate_cost(tokens_used)

            elapsed = time.time() - start_time

            return DocSuggestion(
                updated_doc=updated_doc,
                diff=diff,
                explanation=explanation,
                confidence=confidence,
                provider=self.provider.value,
                model=self.model,
                tokens_used=tokens_used,
                cost_usd=cost,
                generation_time=elapsed
            )

        except Exception as e:
            import traceback
            print(f"\nERROR: LLM documentation generation failed for {entity_name}")
            print(f"   Reason: {str(e)}")
            print(f"   Provider: {self.provider.value}")
            print(f"   Model: {self.model}")
            if context.get('file'):
                print(f"   File: {context['file']}")
            print(f"\n   Full traceback:")
            traceback.print_exc()
            print()
            return self._fallback_suggestion(
                current_doc, change_type, entity_name, context
            )

    def _build_prompt(
        self,
        old_code: str,
        new_code: str,
        current_doc: str,
        change_type: str,
        entity_name: str,
        context: Dict,
        filename: Optional[str],
        language: Optional[str]
    ) -> str:
        """Build the LLM prompt following the template from end-to-end.md"""

        # Detect key changes
        key_changes = self._detect_key_changes(old_code, new_code, language)

        # Extract relevant doc section
        doc_section = self._extract_relevant_section(current_doc, entity_name)

        # Get context values with defaults
        distance = context.get("distance", 0.0)
        mention_count = context.get("mentions", 0)
        line_numbers = context.get("line_numbers", [])

        # Format line number range
        if line_numbers:
            line_range = f"{min(line_numbers)}-{max(line_numbers)}"
        else:
            line_range = "unknown"

        # Build the prompt
        prompt = f"""You are a technical documentation expert. Your job is to write clear, comprehensive API documentation based on code.

TASK: Document the function `{entity_name}` from file `{filename or 'unknown'}`

CHANGE CONTEXT:
- Change type: {change_type.upper()}
- Semantic distance: {distance:.2f}
- Documentation mentions: {mention_count} times

CODE BEING DOCUMENTED:
```{language or 'python'}
{new_code[:2500]}
```

PREVIOUS VERSION (if applicable):
```{language or 'python'}
{old_code[:1500] if old_code else 'N/A - New function'}
```

KEY CHANGES DETECTED:
{self._format_key_changes(key_changes)}

CURRENT DOCUMENTATION:
```markdown
{doc_section[:1500]}
```

INSTRUCTIONS:
1. Write clear, professional documentation for this function
2. Include:
   - Brief description of what the function does
   - Parameters and their types/purposes
   - Return value and type
   - Example usage if relevant
   - Any important notes or warnings
3. If this is an update, note what changed compared to the previous version
4. Be specific and accurate - base everything on the actual code
5. Use markdown formatting

IMPORTANT:
- Set confidence to 0.8-0.95 for high-quality documentation
- Set confidence to 0.5-0.7 for uncertain/incomplete documentation
- Set confidence to 0.2-0.4 only if you cannot generate meaningful docs

Generate your response as JSON:
{{
  "updated_doc": "## {entity_name}\\n\\nYour complete documentation here...",
  "explanation": "What this function does and what changed (if applicable)...",
  "confidence": 0.85
}}
"""

        return prompt

    def _detect_key_changes(
        self,
        old_code: str,
        new_code: str,
        language: Optional[str]
    ) -> List[str]:
        """Detect key changes between old and new code"""
        changes = []

        # Simple heuristic-based detection
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')

        # Check for signature changes
        if language == "python":
            old_defs = [l for l in old_lines if l.strip().startswith('def ')]
            new_defs = [l for l in new_lines if l.strip().startswith('def ')]
            if old_defs != new_defs:
                changes.append("Function signature changed")

            # Check for return type changes
            old_returns = [l for l in old_lines if 'return ' in l]
            new_returns = [l for l in new_lines if 'return ' in l]
            if len(old_returns) != len(new_returns):
                changes.append("Return behavior modified")

        elif language in ["javascript", "typescript"]:
            # Check for function changes
            if 'function' in old_code and 'function' in new_code:
                if old_code.count('function') != new_code.count('function'):
                    changes.append("Function structure changed")

        # Check for added/removed lines
        if len(new_lines) > len(old_lines) * 1.2:
            changes.append(f"Significant code additions ({len(new_lines) - len(old_lines)} lines)")
        elif len(new_lines) < len(old_lines) * 0.8:
            changes.append(f"Significant code removals ({len(old_lines) - len(new_lines)} lines)")

        # Check for logic changes
        old_ifs = old_code.count('if ')
        new_ifs = new_code.count('if ')
        if new_ifs > old_ifs:
            changes.append(f"Added {new_ifs - old_ifs} conditional branches")
        elif new_ifs < old_ifs:
            changes.append(f"Removed {old_ifs - new_ifs} conditional branches")

        if not changes:
            changes.append("Logic or implementation details modified")

        return changes

    def _format_key_changes(self, changes: List[str]) -> str:
        """Format key changes as bullet points"""
        if not changes:
            return "  - No specific changes detected"
        return "\n".join(f"  - {change}" for change in changes)

    def _extract_relevant_section(
        self,
        doc: str,
        entity_name: str
    ) -> str:
        """Extract the relevant section of documentation mentioning the entity"""
        # Simple extraction: find paragraphs containing the entity
        paragraphs = doc.split('\n\n')

        relevant = []
        for para in paragraphs:
            if entity_name.lower() in para.lower():
                relevant.append(para)

        if relevant:
            return '\n\n'.join(relevant)
        else:
            # Return first few paragraphs if no specific mention found
            return '\n\n'.join(paragraphs[:3])

    def _call_llm(self, prompt: str) -> Tuple[str, int]:
        """Call the LLM and return (response_text, tokens_used)"""
        if self.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt)
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt)
        else:
            return self._call_local(prompt)

    def _call_openai(self, prompt: str) -> Tuple[str, int]:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a technical documentation expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"}
        )

        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return response_text, tokens_used

    def _call_anthropic(self, prompt: str) -> Tuple[str, int]:
        """Call Anthropic Claude API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return response_text, tokens_used

    def _call_local(self, prompt: str) -> Tuple[str, int]:
        """Call local model (placeholder for future implementation)"""
        # This would integrate with local models like Llama, Mixtral, etc.
        # For now, return a placeholder
        return '{"updated_doc": "Local model not implemented", "explanation": "Use OpenAI or Anthropic", "confidence": 0.0}', 0

    def _parse_response(
        self,
        response_text: str,
        current_doc: str
    ) -> Tuple[str, str, float]:
        """Parse LLM response and extract updated_doc, explanation, confidence"""
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            updated_doc = data.get("updated_doc", current_doc)
            explanation = data.get("explanation", "No explanation provided")
            confidence = float(data.get("confidence", 0.7))
        except json.JSONDecodeError:
            # Fallback: treat entire response as updated doc
            updated_doc = response_text
            explanation = "LLM response was not in expected JSON format"
            confidence = 0.5

        return updated_doc, explanation, confidence

    def _generate_diff(self, old_doc: str, new_doc: str) -> str:
        """Generate a markdown diff"""
        import difflib

        old_lines = old_doc.split('\n')
        new_lines = new_doc.split('\n')

        diff_lines = []
        diff_lines.append("```diff")

        for line in difflib.unified_diff(
            old_lines, new_lines,
            lineterm='',
            fromfile='current',
            tofile='updated'
        ):
            diff_lines.append(line)

        diff_lines.append("```")

        return '\n'.join(diff_lines)

    def _calculate_cost(self, tokens_used: int) -> float:
        """Calculate estimated cost in USD"""
        if self.model not in self.COSTS:
            # Use average cost if model not found
            model_key = "gpt-4-turbo"
        else:
            model_key = self.model

        # Assume roughly 60% input, 40% output tokens
        input_tokens = int(tokens_used * 0.6)
        output_tokens = int(tokens_used * 0.4)

        cost = (
            (input_tokens / 1000) * self.COSTS[model_key]["input"] +
            (output_tokens / 1000) * self.COSTS[model_key]["output"]
        )

        return round(cost, 4)

    def _fallback_suggestion(
        self,
        current_doc: str,
        change_type: str,
        entity_name: str,
        context: Dict
    ) -> DocSuggestion:
        """Generate a fallback suggestion when LLM is unavailable - uses code analysis"""

        # Try to generate basic documentation from code structure
        new_code = context.get("new_code", "")
        filename = context.get("file", "unknown")

        # Basic documentation template
        doc_lines = []
        doc_lines.append(f"### {entity_name}")
        doc_lines.append("")
        doc_lines.append(f"*Source: `{filename}`*")
        doc_lines.append("")

        # Try to extract docstring if available
        docstring = self._extract_docstring(new_code)
        if docstring:
            doc_lines.append(docstring)
            doc_lines.append("")
        else:
            doc_lines.append(f"Function `{entity_name}` - {change_type} change detected.")
            doc_lines.append("")
            doc_lines.append("**WARNING: Auto-generated stub** - This documentation was generated without LLM.")
            doc_lines.append("Please review and add proper documentation manually.")
            doc_lines.append("")

        # Try to extract function signature
        signature = self._extract_function_signature(new_code, entity_name)
        if signature:
            doc_lines.append("**Signature:**")
            doc_lines.append(f"```python")
            doc_lines.append(signature)
            doc_lines.append("```")
            doc_lines.append("")

        updated_doc = "\n".join(doc_lines)

        explanation = f"WARNING: LLM unavailable - Generated basic documentation stub from code analysis. The function {entity_name} has a {change_type.upper()} change. Manual review and enhancement required."

        return DocSuggestion(
            updated_doc=updated_doc,
            diff=self._generate_diff(current_doc, updated_doc),
            explanation=explanation,
            confidence=0.1,  # Very low confidence for stubs
            provider="fallback",
            model="code-analysis",
            tokens_used=0,
            cost_usd=0.0,
            generation_time=0.0
        )

    def _extract_docstring(self, code: str) -> Optional[str]:
        """Extract docstring from Python code"""
        try:
            import ast
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        return docstring
        except:
            pass
        return None

    def _extract_function_signature(self, code: str, func_name: str) -> Optional[str]:
        """Extract function signature from code"""
        try:
            import ast
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    # Get the function definition line
                    lines = code.split('\n')
                    if node.lineno <= len(lines):
                        # Find the complete function signature (may span multiple lines)
                        sig_lines = []
                        for i in range(node.lineno - 1, min(node.lineno + 5, len(lines))):
                            sig_lines.append(lines[i])
                            if ':' in lines[i]:
                                break
                        return '\n'.join(sig_lines)
        except:
            pass

        # Fallback: regex search
        import re
        pattern = rf"def\s+{re.escape(func_name)}\s*\([^)]*\)"
        match = re.search(pattern, code)
        if match:
            return match.group(0)

        return None

    def generate_batch(
        self,
        requests: List[Dict]
    ) -> List[DocSuggestion]:
        """
        Generate multiple doc updates in batch.

        Args:
            requests: List of dicts with same parameters as generate_doc_update()

        Returns:
            List of DocSuggestion objects
        """
        results = []

        for req in requests:
            suggestion = self.generate_doc_update(**req)
            results.append(suggestion)

            # Small delay to respect rate limits
            time.sleep(0.5)

        return results


# Convenience functions

def generate_doc_update(
    old_code: str,
    new_code: str,
    current_doc: str,
    change_type: str,
    entity_name: str,
    provider: str = "openai",
    api_key: Optional[str] = None
) -> DocSuggestion:
    """
    Convenience function to generate a single doc update.

    Args:
        old_code: Previous code
        new_code: New code
        current_doc: Current documentation
        change_type: "major", "minor", or "rewrite"
        entity_name: Function/class name
        provider: "openai", "anthropic", or "local"
        api_key: API key (or None to use environment)

    Returns:
        DocSuggestion
    """
    generator = LLMDocGenerator(provider=provider, api_key=api_key)
    return generator.generate_doc_update(
        old_code=old_code,
        new_code=new_code,
        current_doc=current_doc,
        change_type=change_type,
        entity_name=entity_name,
        context={}
    )


# Self-test
if __name__ == "__main__":
    print("LLMDocGenerator - Component 2")
    print("=" * 80)
    print("\nThis module uses LLM to generate documentation updates.")
    print("\nSupported providers:")
    print("  - OpenAI (GPT-4, GPT-3.5)")
    print("  - Anthropic (Claude)")
    print("  - Local models (coming soon)")
    print("\nUsage:")
    print("  from llm_doc_generator import LLMDocGenerator")
    print("  ")
    print("  generator = LLMDocGenerator(provider='openai', api_key='...')")
    print("  suggestion = generator.generate_doc_update(")
    print("      old_code=old_code,")
    print("      new_code=new_code,")
    print("      current_doc=current_doc,")
    print("      change_type='major',")
    print("      entity_name='validate_password',")
    print("      context={'mentions': 4}")
    print("  )")
    print("\nSet API keys:")
    print("  export OPENAI_API_KEY='sk-...'")
    print("  export ANTHROPIC_API_KEY='sk-ant-...'")
