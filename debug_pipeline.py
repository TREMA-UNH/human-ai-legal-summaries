#!/usr/bin/env python3
"""
Debug script to test pipeline components individually
"""
import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_nugget_generation():
    """Test nugget generation with a simple text"""
    print("Testing nugget generation...")
    
    try:
        from vanilla_nugget_generation.DepositionNuggetGeneration import DepositionNuggetGenerator
        
        # Create a simple test deposition
        test_content = """
Q: What is your name?
A: My name is John Doe.

Q: What happened on the day of the incident?
A: I was driving to work when another car ran a red light and hit me.

Q: Were you injured?
A: Yes, I suffered a broken arm and whiplash.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            test_deposition_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_output_path = f.name
        
        print(f"Test deposition: {test_deposition_path}")
        print(f"Test output: {test_output_path}")
        
        # Try to create generator
        generator = DepositionNuggetGenerator(
            input_path=test_deposition_path,
            output_path=test_output_path
        )
        
        print("✓ DepositionNuggetGenerator created successfully")
        
        # Try to run it
        generator.run()
        
        print("✓ Nugget generation completed successfully")
        
        # Check if output file exists
        if Path(test_output_path).exists():
            print("✓ Output file created")
            with open(test_output_path, 'r') as f:
                result = f.read()
                print(f"Output preview: {result[:200]}...")
        else:
            print("❌ Output file not created")
        
        # Cleanup
        os.unlink(test_deposition_path)
        os.unlink(test_output_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in nugget generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_evaluation():
    """Test evaluation component"""
    print("\nTesting evaluation...")
    
    try:
        from vanilla_nuggetbased_evaluation.predefined_nuggetbased_evaluation import EnhancedSummaryEvaluator
        
        evaluator = EnhancedSummaryEvaluator()
        print("✓ EnhancedSummaryEvaluator created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_citation_linking():
    """Test citation linking"""
    print("\nTesting citation linking...")
    
    try:
        from citation_retriever.citation_linker import CitationLinker
        from citation_retriever.deposition_processor import DepositionProcessor
        from citation_retriever.summary_parser import Summary
        
        print("✓ Citation components imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in citation linking: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Debugging NextPoint pipeline components...\n")
    
    success_count = 0
    tests = [
        ("Citation Linking", test_citation_linking),
        ("Evaluation", test_evaluation),
        ("Nugget Generation", test_nugget_generation),
    ]
    
    for test_name, test_func in tests:
        print(f"=== {test_name} ===")
        if test_func():
            success_count += 1
        print()
    
    print(f"Results: {success_count}/{len(tests)} tests passed")
    
    if success_count == len(tests):
        print("🎉 All components working!")
    else:
        print("⚠️  Some components have issues")