"""Compatibility shim. Script moved to tools/checks/check_endpoint_contexts.py

This wrapper keeps the old entry point working.
"""

import runpy

if __name__ == "__main__":
    runpy.run_module("tools.checks.check_endpoint_contexts", run_name="__main__")
