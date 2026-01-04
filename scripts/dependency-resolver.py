#!/usr/bin/env python3
"""
dependency-resolver.py - Resolves and validates plugin dependencies

This script validates plugin dependencies, detects circular dependencies,
and resolves version conflicts in the plugin registry.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque
import yaml


class VersionConstraint:
    """Represents a version constraint (e.g., >=1.0.0, ~>1.2.0)"""
    
    def __init__(self, constraint: str):
        self.constraint = constraint
        self.operator, self.version = self._parse(constraint)
    
    def _parse(self, constraint: str) -> Tuple[str, str]:
        """Parse version constraint into operator and version"""
        match = re.match(r'^(>=|<=|>|<|~>|=|\^)(.+)$', constraint)
        if not match:
            raise ValueError(f"Invalid version constraint: {constraint}")
        return match.group(1), match.group(2)
    
    def satisfies(self, version: str) -> bool:
        """Check if a version satisfies this constraint"""
        # Normalize versions for comparison
        v1_parts = self._parse_version(self.version)
        v2_parts = self._parse_version(version)
        
        if self.operator == '=':
            return self.version == version
        elif self.operator == '>=':
            return self._compare_versions(v2_parts, v1_parts) >= 0
        elif self.operator == '<=':
            return self._compare_versions(v2_parts, v1_parts) <= 0
        elif self.operator == '>':
            return self._compare_versions(v2_parts, v1_parts) > 0
        elif self.operator == '<':
            return self._compare_versions(v2_parts, v1_parts) < 0
        elif self.operator == '~>':
            # Pessimistic operator: ~>1.2.3 means >=1.2.3 and <1.3.0
            return (self._compare_versions(v2_parts, v1_parts) >= 0 and
                    self._compare_versions(v2_parts, (v1_parts[0], v1_parts[1] + 1, 0)) < 0)
        elif self.operator == '^':
            # Caret operator: ^1.2.3 means >=1.2.3 and <2.0.0
            return (self._compare_versions(v2_parts, v1_parts) >= 0 and
                    self._compare_versions(v2_parts, (v1_parts[0] + 1, 0, 0)) < 0)
        return False
    
    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse semantic version into (major, minor, patch)"""
        # Remove pre-release and build metadata
        version = re.sub(r'[-+].*$', '', version)
        parts = version.split('.')
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0
        )
    
    def _compare_versions(self, v1: Tuple[int, int, int], v2: Tuple[int, int, int]) -> int:
        """Compare two version tuples. Returns -1, 0, or 1"""
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        return 0


class DependencyResolver:
    """Resolves and validates plugin dependencies"""
    
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, dict] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
    
    def load_plugins(self):
        """Load all plugin manifests from the plugins directory"""
        if not self.plugins_dir.exists():
            return
        
        for manifest_file in self.plugins_dir.glob('*.potion'):
            try:
                with open(manifest_file, 'r') as f:
                    manifest = yaml.safe_load(f)
                    name = manifest.get('name')
                    if name:
                        self.plugins[name] = manifest
            except Exception as e:
                print(f"Warning: Failed to load {manifest_file}: {e}", file=sys.stderr)
    
    def build_dependency_graph(self):
        """Build dependency graph from loaded plugins"""
        for name, manifest in self.plugins.items():
            dependencies = manifest.get('dependencies', [])
            for dep in dependencies:
                dep_name = dep.get('name')
                if dep_name:
                    self.dependency_graph[name].add(dep_name)
                    self.reverse_graph[dep_name].add(name)
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            rec_stack.remove(node)
            path.pop()
        
        for node in self.plugins.keys():
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def validate_dependencies(self, manifest: dict) -> Tuple[bool, List[str]]:
        """Validate dependencies for a single plugin manifest"""
        errors = []
        name = manifest.get('name')
        dependencies = manifest.get('dependencies', [])
        
        for dep in dependencies:
            dep_name = dep.get('name')
            if not dep_name:
                errors.append(f"Invalid dependency: missing name")
                continue
            
            # Check if dependency exists in registry
            if dep_name not in self.plugins:
                errors.append(f"Dependency '{dep_name}' not found in registry")
                continue
            
            # Check version constraint
            dep_version = dep.get('version')
            if dep_version:
                try:
                    constraint = VersionConstraint(dep_version)
                    plugin_version = self.plugins[dep_name].get('version', '0.0.0')
                    if not constraint.satisfies(plugin_version):
                        errors.append(
                            f"Dependency '{dep_name}' version '{plugin_version}' "
                            f"does not satisfy constraint '{dep_version}'"
                        )
                except ValueError as e:
                    errors.append(f"Invalid version constraint for '{dep_name}': {e}")
        
        return len(errors) == 0, errors
    
    def resolve_all_dependencies(self) -> Tuple[bool, List[str]]:
        """Resolve and validate all plugin dependencies"""
        errors = []
        
        # Detect circular dependencies
        cycles = self.detect_circular_dependencies()
        if cycles:
            for cycle in cycles:
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        # Validate each plugin's dependencies
        for name, manifest in self.plugins.items():
            valid, plugin_errors = self.validate_dependencies(manifest)
            if not valid:
                errors.extend([f"[{name}] {e}" for e in plugin_errors])
        
        return len(errors) == 0, errors


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: dependency-resolver.py <plugins-dir> [manifest-file]", file=sys.stderr)
        sys.exit(1)
    
    plugins_dir = Path(sys.argv[1])
    manifest_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    resolver = DependencyResolver(plugins_dir)
    resolver.load_plugins()
    resolver.build_dependency_graph()
    
    if manifest_file:
        # Validate single manifest
        try:
            with open(manifest_file, 'r') as f:
                manifest = yaml.safe_load(f)
            
            valid, errors = resolver.validate_dependencies(manifest)
            if not valid:
                print("Dependency validation failed:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                sys.exit(1)
            
            print("✓ All dependencies are valid")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Validate all plugins
        valid, errors = resolver.resolve_all_dependencies()
        if not valid:
            print("Dependency resolution failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        
        print("✓ All dependencies resolved successfully")
        print(f"  Total plugins: {len(resolver.plugins)}")
        print(f"  Total dependencies: {sum(len(deps) for deps in resolver.dependency_graph.values())}")


if __name__ == "__main__":
    main()

