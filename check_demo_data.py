#!/usr/bin/env python3
"""Compatibility shim. Script moved to tools/checks/check_demo_data.py

This wrapper keeps the old entry point working.
"""

import runpy

if __name__ == "__main__":
    runpy.run_module("tools.checks.check_demo_data", run_name="__main__")
