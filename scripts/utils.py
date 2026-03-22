#!/usr/bin/env python3
"""
Common utility functions for Movie Notifier
"""

import os


def get_project_root() -> str:
    """
    Get the project root directory (parent of scripts directory).

    Returns:
        Absolute path to project root
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def resolve_path(relative_path: str, relative_to_root: bool = True) -> str:
    """
    Resolve a relative path to an absolute path.

    Args:
        relative_path: The relative path to resolve
        relative_to_root: If True, resolve relative to project root

    Returns:
        Absolute path
    """
    if os.path.isabs(relative_path):
        return relative_path

    if relative_to_root:
        return os.path.join(get_project_root(), relative_path)
    return os.path.abspath(relative_path)
