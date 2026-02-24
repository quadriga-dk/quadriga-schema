#!/usr/bin/env python3
"""Re-serialize a JSON file with ASCII-only encoding (non-ASCII → \\uXXXX).

This ensures browsers display characters correctly when served without
a charset=utf-8 Content-Type header (e.g., on GitHub Pages).

Usage: ascii-escape-json.py <source> <destination>
"""

import json
import sys

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <source> <destination>", file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1]) as f:
    data = json.load(f)

with open(sys.argv[2], "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=True)
    f.write("\n")
