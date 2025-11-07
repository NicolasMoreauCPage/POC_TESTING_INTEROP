"""Compatibility shim. Script moved to tools/checks/check_logs.py

This wrapper keeps the old entry point working.
"""

import runpy

if __name__ == "__main__":
    runpy.run_module("tools.checks.check_logs", run_name="__main__")
