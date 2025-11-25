import sys
import json
import io
import contextlib
import runpy
from typing import Any, Dict


def load_user_module(path: str) -> Dict[str, Any]:
    return runpy.run_path(path, init_globals={})


def ensure_main_callable(ns: Dict[str, Any]):
    fn = ns.get("main")
    if fn is None:
        raise RuntimeError("Script must define a function main()")
    if not callable(fn):
        raise RuntimeError("main() must be a function")
    return fn


def ensure_json(value: Any) -> Dict[str, Any]:
    if value is None:
        raise RuntimeError("main() must return a JSON object, got None")

    if not isinstance(value, dict):
        raise RuntimeError("main() must return a JSON object (dict)")

    try:
        json.dumps(value)  # check serializable
        return value
    except Exception as e:
        raise RuntimeError(f"Return value is not JSON-serializable: {e}")


def run_user_main(path: str) -> Dict[str, Any]:
    buf = io.StringIO()

    try:
        with contextlib.redirect_stdout(buf):
            ns = load_user_module(path)
            main_fn = ensure_main_callable(ns)
            out = main_fn()

        stdout_val = buf.getvalue()
        out_json = ensure_json(out)

        return {"result": out_json, "stdout": stdout_val}

    finally:
        buf.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: sandbox_runner.py <script.py>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]

    try:
        payload = run_user_main(path)
        print(json.dumps(payload))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("Internal error while executing script", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
