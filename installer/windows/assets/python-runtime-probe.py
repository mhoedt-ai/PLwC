from __future__ import annotations

import importlib
import site
import sys
import traceback
from pathlib import Path


DEFAULT_MODULES = ("mcp", "qdrant_client", "onnxruntime", "fastembed")


def main() -> int:
    if len(sys.argv) < 2:
        return 2

    log_path = Path(sys.argv[1])
    modules = tuple(sys.argv[2:]) or DEFAULT_MODULES
    failures: list[str] = []

    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        log.write("\n[PLwC Python runtime probe]\n")
        log.write(f"executable={sys.executable}\n")
        log.write(f"version={sys.version}\n")
        log.write(f"enable_user_site={site.ENABLE_USER_SITE}\n")
        log.write(f"user_site={site.getusersitepackages()}\n")
        log.write("sys_path=\n")
        for entry in sys.path:
            log.write(f"  {entry}\n")

        for module_name in modules:
            log.write(f"import={module_name} status=starting\n")
            log.flush()
            try:
                module = importlib.import_module(module_name)
                module_path = getattr(module, "__file__", "<no __file__>")
                log.write(f"import={module_name} status=ok path={module_path}\n")
            except BaseException:
                failures.append(module_name)
                log.write(f"import={module_name} status=failed\n")
                traceback.print_exc(file=log)

        if failures:
            log.write("failed_modules=" + ",".join(failures) + "\n")
            return 1

        log.write("runtime_probe=ok\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
