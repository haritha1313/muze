"""
Test LLM Documentation Generator locally before pushing
"""

import os
from llm_doc_generator import LLMDocGenerator

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    print("   Install with: pip install python-dotenv")
except:
    pass

# Sample code for testing
OLD_CODE = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
"""

NEW_CODE = """
def calculate_total(items, tax_rate=0.0):
    \"\"\"Calculate total price with optional tax.\"\"\"
    subtotal = sum(item['price'] for item in items)
    total = subtotal * (1 + tax_rate)
    return total
"""

CURRENT_DOC = """
## calculate_total

Calculates the total price from a list of items.
"""

def test_anthropic():
    """Test with Anthropic Claude"""
    print("Testing Anthropic Claude...")
    print("=" * 80)

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set in environment!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return False

    try:
        # Initialize generator
        generator = LLMDocGenerator(
            provider="anthropic",
            api_key=api_key,
            temperature=0.3
        )

        print(f"✓ Using model: {generator.model}")
        print(f"✓ Provider: {generator.provider.value}")
        print()

        # Generate documentation
        print("Generating documentation...")
        result = generator.generate_doc_update(
            old_code=OLD_CODE,
            new_code=NEW_CODE,
            current_doc=CURRENT_DOC,
            change_type="major",
            entity_name="calculate_total",
            context={
                "mentions": 3,
                "file": "test.py",
                "distance": 0.15
            },
            filename="test.py",
            language="python"
        )

        print("\n" + "=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print(f"\nModel: {result.model}")
        print(f"Provider: {result.provider}")
        print(f"Confidence: {result.confidence}")
        print(f"Tokens used: {result.tokens_used}")
        print(f"Cost: ${result.cost_usd}")
        print(f"Time: {result.generation_time:.2f}s")

        print("\n📝 Generated Documentation:")
        print("-" * 80)
        print(result.updated_doc)

        print("\n💡 Explanation:")
        print("-" * 80)
        print(result.explanation)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openai():
    """Test with OpenAI (optional)"""
    print("\n\nTesting OpenAI GPT-4...")
    print("=" * 80)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping OpenAI test")
        return None

    try:
        generator = LLMDocGenerator(
            provider="openai",
            api_key=api_key,
            temperature=0.3
        )

        print(f"✓ Using model: {generator.model}")

        result = generator.generate_doc_update(
            old_code=OLD_CODE,
            new_code=NEW_CODE,
            current_doc=CURRENT_DOC,
            change_type="major",
            entity_name="calculate_total",
            context={
                "mentions": 3,
                "file": "test.py"
            }
        )

        print(f"\n✅ OpenAI test passed!")
        print(f"Model: {result.model}, Confidence: {result.confidence}")
        return True

    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing LLM Documentation Generator")
    print("=" * 80)
    print()

    # Test Anthropic (required for your workflow)
    success = test_anthropic()

    # Optional: test OpenAI
    test_openai()

    print("\n" + "=" * 80)
    if success:
        print("✅ All tests passed! Safe to push.")
    else:
        print("❌ Tests failed. Fix issues before pushing.")
    print("=" * 80)
