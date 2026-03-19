"""Debug script to test upload and see full error"""
import sys
sys.path.insert(0, 'f:\\samad\\chatobot\\rag_system')

import asyncio
from app.services.hybrid_processor import hybrid_processor
from pathlib import Path

async def test_hybrid():
    """Test hybrid processing with text file"""
    test_file = Path("test-upload.txt")
    
    if not test_file.exists():
        print("Creating test file...")
        test_file.write_text("Test content for upload")
    
    print(f"Testing hybrid processing on {test_file}")
    
    try:
        result = await hybrid_processor.process_document(
            file_path=str(test_file),
            filename="test-upload.txt",
            processing_mode="hybrid",
            save_images=True
        )
        print(f"Success! Result: {result}")
    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hybrid())
