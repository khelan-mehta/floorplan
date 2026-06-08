"""Dump the FastAPI OpenAPI document to stdout (or a file arg).

Used to generate the typed TS client:
    python scripts/export_openapi.py openapi.json
    npx openapi-typescript openapi.json -o ../../packages/api-client/src/schema.d.ts
"""

from __future__ import annotations

import json
import sys

from app.main import app


def main() -> None:
    spec = app.openapi()
    out = json.dumps(spec, indent=2)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            fh.write(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
