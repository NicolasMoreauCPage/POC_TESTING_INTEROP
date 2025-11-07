#!/usr/bin/env python3
"""Compatibility shim. Script moved to tools/apply_all_migrations.py

This wrapper keeps the old entry point working.
"""

import runpy

if __name__ == "__main__":
    runpy.run_module("tools.apply_all_migrations", run_name="__main__")
