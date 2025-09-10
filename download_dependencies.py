#!/usr/bin/env python3
"""
Download dependencies script for CodeSight AST parsers.

This script downloads required JAR libraries for Java AST parsing
and sets up the proper directory structure.
"""

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Configuration
DEPENDENCIES: Dict[str, Dict[str, Any]] = {
    'javaparser-core': {
        'version': '3.24.2',
        'url': 'https://repo1.maven.org/maven2/com/github/javaparser/javaparser-core/3.24.2/javaparser-core-3.24.2.jar',
        'filename': 'javaparser-core-3.24.2.jar',
        'description': 'JavaParser core library for Java AST parsing',
        'required': True
    },
    'javaparser-symbol-solver': {
        'version': '3.24.2', 
        'url': 'https://repo1.maven.org/maven2/com/github/javaparser/javaparser-symbol-solver-core/3.24.2/javaparser-symbol-solver-core-3.24.2.jar',
        'filename': 'javaparser-symbol-solver-core-3.24.2.jar',
        'description': 'JavaParser symbol solver for enhanced AST analysis',
        'required': False
    }
}


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def create_lib_directory() -> Path:
    """Create lib directory if it doesn't exist."""
    lib_dir = get_project_root() / 'lib'
    lib_dir.mkdir(exist_ok=True)
    print(f"✓ Created/verified lib directory: {lib_dir}")
    return lib_dir


def download_file(url: str, target_path: Path, description: str) -> bool:
    """
    Download a file from URL to target path.
    
    Args:
        url: Download URL
        target_path: Target file path
        description: Human-readable description
        
    Returns:
        True if download successful
    """
    try:
        print(f"📥 Downloading {description}...")
        print(f"   URL: {url}")
        print(f"   Target: {target_path}")
        
        # Check if file already exists
        if target_path.exists():
            file_size = target_path.stat().st_size
            print(f"   File already exists ({file_size:,} bytes)")
            
            # Verify it's not empty/corrupted
            if file_size > 1000:  # Reasonable minimum size for JAR files
                print(f"✓ Using existing {target_path.name}")
                return True
            else:
                print("⚠️  Existing file seems corrupted, re-downloading...")
                target_path.unlink()
        
        # Download with progress
        def progress_hook(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                print(f"\r   Progress: {percent}%", end='', flush=True)
        
        urllib.request.urlretrieve(url, target_path, progress_hook)
        print()  # New line after progress
        
        # Verify download
        if target_path.exists():
            file_size = target_path.stat().st_size
            print(f"✓ Downloaded {target_path.name} ({file_size:,} bytes)")
            return True
        else:
            print(f"❌ Failed to download {target_path.name}")
            return False
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP error downloading {description}: {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ Network error downloading {description}: {e}")
        return False
    except (OSError, IOError) as e:
        print(f"❌ File system error downloading {description}: {e}")
        return False
    except Exception as e:  # pylint: disable=broad-except
        print(f"❌ Unexpected error downloading {description}: {e}")
        return False


def verify_downloads(lib_dir: Path) -> Dict[str, bool]:
    """
    Verify all downloaded files exist and are valid.
    
    Args:
        lib_dir: Library directory path
        
    Returns:
        Dictionary mapping dependency names to verification status
    """
    results = {}
    
    print("\n🔍 Verifying downloads...")
    
    for dep_name, dep_info in DEPENDENCIES.items():
        file_path = lib_dir / dep_info['filename']
        
        if file_path.exists():
            file_size = file_path.stat().st_size
            if file_size > 1000:  # Reasonable minimum
                print(f"✓ {dep_info['filename']} ({file_size:,} bytes)")
                results[dep_name] = True
            else:
                print(f"❌ {dep_info['filename']} seems corrupted ({file_size} bytes)")
                results[dep_name] = False
        else:
            if dep_info['required']:
                print(f"❌ {dep_info['filename']} missing (required)")
                results[dep_name] = False
            else:
                print(f"⚠️  {dep_info['filename']} missing (optional)")
                results[dep_name] = False
    
    return results


def create_version_info(lib_dir: Path) -> None:
    """Create a version info file documenting downloaded dependencies."""
    version_file = lib_dir / 'VERSION_INFO.txt'
    
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write("CodeSight AST Parser Dependencies\n")
        f.write("=" * 40 + "\n\n")
        
        for dep_name, dep_info in DEPENDENCIES.items():
            f.write(f"Dependency: {dep_name}\n")
            f.write(f"Version: {dep_info['version']}\n")
            f.write(f"Filename: {dep_info['filename']}\n")
            f.write(f"Description: {dep_info['description']}\n")
            f.write(f"Required: {'Yes' if dep_info['required'] else 'No'}\n")
            f.write(f"URL: {dep_info['url']}\n")
            f.write("-" * 40 + "\n")
        
        f.write(f"\nDownloaded on: {Path(__file__).stat().st_mtime}\n")
    
    print(f"📝 Created version info: {version_file}")


def main() -> None:
    """Main download script."""
    print("CodeSight Dependency Downloader")
    print("=" * 40)
    
    # Setup
    project_root = get_project_root()
    print(f"🏠 Project root: {project_root}")
    
    lib_dir = create_lib_directory()
    
    # Download dependencies
    print(f"\n📦 Downloading {len(DEPENDENCIES)} dependencies...")
    
    success_count = 0
    for dep_name, dep_info in DEPENDENCIES.items():
        target_path = lib_dir / dep_info['filename']
        
        if download_file(dep_info['url'], target_path, dep_info['description']):
            success_count += 1
        elif dep_info['required']:
            print(f"❌ Failed to download required dependency: {dep_name}")
        else:
            print(f"⚠️  Failed to download optional dependency: {dep_name}")
        
        print()  # Blank line between downloads
    
    # Verification
    verification_results = verify_downloads(lib_dir)
    
    # Summary
    print("\n📊 Download Summary:")
    print(f"   Total dependencies: {len(DEPENDENCIES)}")
    print(f"   Successfully downloaded: {success_count}")
    print(f"   Required dependencies: {sum(1 for d in DEPENDENCIES.values() if d['required'])}")
    
    required_success = sum(1 for name, success in verification_results.items() 
                          if success and DEPENDENCIES[name]['required'])
    required_total = sum(1 for d in DEPENDENCIES.values() if d['required'])
    
    if required_success == required_total:
        print("✅ All required dependencies downloaded successfully!")
        create_version_info(lib_dir)
        
        print("\n🚀 Setup complete! Java AST parsing is now available.")
        print(f"   Library directory: {lib_dir}")
        print("   Required JARs: ✓")
        print("   JPype integration: Ready")
        
    else:
        print(f"❌ Missing {required_total - required_success} required dependencies")
        print("   Java AST parsing will use fallback regex mode")
    
    print("\n💡 Next steps:")
    print("   1. Ensure Java is installed: java -version")
    print("   2. Run CodeSight Step 02 AST extraction")
    print("   3. Check logs for JPype initialization status")


if __name__ == '__main__':
    main()
