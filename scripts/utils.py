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
