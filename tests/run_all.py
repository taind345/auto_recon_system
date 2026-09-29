#!/usr/bin/env python3
"""Run the full AUTO_RECON suite: python unittest + node frontend flow (if node exists).

Usage (repo root):  python3 tests/run_all.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

fails = 0

print("=== [1/2] python unittest ===")
p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"])
fails += 0 if p.returncode == 0 else 1

print("=== [2/2] node frontend flow ===")
node = shutil.which("node")
if node:
    p2 = subprocess.run([node, "tests/frontend_flow.js"])
    fails += 0 if p2.returncode == 0 else 1
else:
    print("SKIP (node not found)")

print("RESULT:", "PASS" if fails == 0 else "FAIL")
sys.exit(1 if fails else 0)
