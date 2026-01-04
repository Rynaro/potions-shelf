#!/usr/bin/env python3
"""
generate-index.py - Generates index.json from all plugin manifest files

This script scans the plugins directory, reads all .potion manifest files,
and generates a searchable index.json file for the registry.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import yaml


def load_manifest(file_path: Path) -> Dict:
    """Load and parse a manifest file"""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Failed to load {file_path}: {e}", file=sys.stderr)
        return None


def generate_index(plugins_dir: Path, output_file: Path) -> bool:
    """Generate index.json from all plugin manifests"""
    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}", file=sys.stderr)
        return False
    
    plugins = []
    categories = defaultdict(list)
    
    # Load all manifest files
    manifest_files = sorted(plugins_dir.glob('*.potion'))
    
    if not manifest_files:
        print("Warning: No manifest files found in plugins directory", file=sys.stderr)
    
    for manifest_file in manifest_files:
        manifest = load_manifest(manifest_file)
        if not manifest:
            continue
        
        # Extract plugin data
        plugin_data = {
            "name": manifest.get("name"),
            "version": manifest.get("version"),
            "description": manifest.get("description"),
            "author": manifest.get("author"),
            "repository": manifest.get("repository"),
            "homepage": manifest.get("homepage"),
            "license": manifest.get("license"),
            "tags": manifest.get("tags", []),
            "verified": manifest.get("verified", False),
            "potionfile_path": manifest.get("potionfile_path", "Potionfile"),
            "min_potions_version": manifest.get("min_potions_version"),
            "max_potions_version": manifest.get("max_potions_version"),
            "dependencies": manifest.get("dependencies", []),
            "install": manifest.get("install", {"type": "git", "path": "/"}),
        }
        
        # Remove None values
        plugin_data = {k: v for k, v in plugin_data.items() if v is not None}
        
        plugins.append(plugin_data)
        
        # Build category index
        for tag in manifest.get("tags", []):
            categories[tag].append(manifest.get("name"))
    
    # Create index structure
    index = {
        "version": "1.0.0",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_plugins": len(plugins),
        "plugins": sorted(plugins, key=lambda p: p.get("name", "")),
        "categories": dict(sorted(categories.items())),
    }
    
    # Write index file
    try:
        with open(output_file, 'w') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"✓ Generated index with {len(plugins)} plugins")
        print(f"  Categories: {len(categories)}")
        print(f"  Output: {output_file}")
        return True
    except Exception as e:
        print(f"Error: Failed to write index file: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: generate-index.py <plugins-dir> <output-file>", file=sys.stderr)
        sys.exit(1)
    
    plugins_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    success = generate_index(plugins_dir, output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

