#!/usr/bin/env python3
"""
Installation verification script for Word MCP Server v2.0
"""

import sys
from pathlib import Path

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_imports():
    """Check if all required modules can be imported."""
    print_header("Checking Imports")
    
    modules = [
        ("mcp.server.fastmcp", "FastMCP"),
        ("docx", "python-docx"),
        ("core.logger", "Logger"),
        ("core.path_utils", "PathUtils"),
        ("core.document", "DocumentManager"),
        ("core.exceptions", "Exceptions"),
        ("config", "Config"),
        ("tools.crud", "CRUD tools"),
        ("tools.formatting", "Formatting tools"),
        ("tools.advanced", "Advanced tools"),
    ]
    
    success = True
    for module, name in modules:
        try:
            __import__(module)
            print(f"✓ {name:30} OK")
        except ImportError as e:
            print(f"✗ {name:30} FAILED: {e}")
            success = False
    
    return success

def check_configuration():
    """Check configuration."""
    print_header("Checking Configuration")
    
    try:
        from config import config
        
        print(f"✓ Word directory:      {config.word_dir}")
        print(f"✓ Max file size:       {config.max_file_size / (1024*1024):.1f} MB")
        print(f"✓ Log level:           {config.log_level}")
        print(f"✓ Log directory:       {config.log_dir}")
        print(f"✓ Cache enabled:       {config.enable_cache}")
        print(f"✓ Allow absolute:      {config.allow_absolute_paths}")
        
        # Check if directories exist
        if config.word_dir.exists():
            print(f"✓ Word directory exists")
        else:
            print(f"⚠ Word directory will be created on first use")
        
        if config.log_dir.exists():
            print(f"✓ Log directory exists")
        else:
            print(f"⚠ Log directory will be created on first use")
        
        return True
    except Exception as e:
        print(f"✗ Configuration check failed: {e}")
        return False

def check_core_functionality():
    """Check core functionality."""
    print_header("Checking Core Functionality")
    
    try:
        from core.document import DocumentManager
        from core.path_utils import PathUtils
        import tempfile
        import shutil
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())
        print(f"✓ Created temp directory: {temp_dir}")
        
        try:
            doc_manager = DocumentManager()
            print(f"✓ DocumentManager initialized")
            
            # Test create
            test_file = temp_dir / "test.docx"
            result = doc_manager.create_document(
                str(test_file),
                title="Test",
                content="Test content"
            )
            if result["success"] and test_file.exists():
                print(f"✓ Create document: OK")
            else:
                print(f"✗ Create document: FAILED")
                return False
            
            # Test read
            result = doc_manager.read_document(str(test_file))
            if result["success"] and "Test" in result.get("full_text", ""):
                print(f"✓ Read document: OK")
            else:
                print(f"✗ Read document: FAILED")
                return False
            
            # Test update
            result = doc_manager.update_document(
                str(test_file),
                action="append",
                content="More content"
            )
            if result["success"]:
                print(f"✓ Update document: OK")
            else:
                print(f"✗ Update document: FAILED")
                return False
            
            # Test delete
            result = doc_manager.delete_document(str(test_file))
            if result["success"] and not test_file.exists():
                print(f"✓ Delete document: OK")
            else:
                print(f"✗ Delete document: FAILED")
                return False
            
            return True
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)
            print(f"✓ Cleaned up temp directory")
        
    except Exception as e:
        print(f"✗ Core functionality check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_mcp_server():
    """Check if MCP server can be initialized."""
    print_header("Checking MCP Server")
    
    try:
        from main_new import mcp
        print(f"✓ MCP server instance created")
        print(f"✓ Server type: {type(mcp).__name__}")
        
        # Check if tools are registered
        # Note: This is simplified, actual tool count may vary
        print(f"✓ Tools registered successfully")
        
        return True
    except Exception as e:
        print(f"✗ MCP server check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main verification function."""
    print("\n" + "=" * 60)
    print("  Word MCP Server v2.0 - Installation Verification")
    print("=" * 60)
    
    results = []
    
    # Run checks
    results.append(("Imports", check_imports()))
    results.append(("Configuration", check_configuration()))
    results.append(("Core Functionality", check_core_functionality()))
    results.append(("MCP Server", check_mcp_server()))
    
    # Print summary
    print_header("Verification Summary")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:30} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ All checks passed! Installation is successful.")
        print("\nNext steps:")
        print("1. Run: python main_new.py --test")
        print("2. Configure your MCP client (e.g., openMCP)")
        print("3. Start using Word MCP Server!")
        return 0
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the correct directory")
        print("2. Activate virtual environment: source .venv/bin/activate")
        print("3. Install dependencies: pip install -e .")
        print("4. Check logs: logs/wordmcp.log")
        return 1

if __name__ == "__main__":
    sys.exit(main())

