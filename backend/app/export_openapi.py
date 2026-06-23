"""Export the OpenAPI schema to stdout — SoT for the frontend contract (§5.1).

Usage: python -m app.export_openapi > openapi.json
The frontend regenerates its typed client from this file (npm run gen:api) and must
never hand-edit the generated output (§5.1 drift control).
"""
from __future__ import annotations

import json

from app.main import create_app


def main() -> None:
    app = create_app()
    print(json.dumps(app.openapi(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
