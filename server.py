from pathlib import Path
import sys

BUNDLE_ROOT = Path(__file__).resolve().parent
SRC = BUNDLE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from plwc_gateway.mcp.server import main

if __name__ == "__main__":
    main()
