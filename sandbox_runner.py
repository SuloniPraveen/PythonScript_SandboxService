import sys
import json
import io
import contextlib
import runpy
import traceback
from typing import Any, Dict


def load_user_module(script_path: str) -> Dict[str, Any]:
    """
    Load the user's script file into its own namespace.
    """
    return runpy.run_path(script_path, init_globals={})


def ensure_main_callable(ns: Dict[str, Any]):
    """
    Ensure there is a callable main() in the namespace.
    Raises RuntimeError if not.
    """
    main_fn = ns.get("main")
    if main_fn is None:
        raise RuntimeError("Script must define a function main()")
    if not callable(main_fn):
        raise RuntimeError("main must be callable")
    return main_fn


def ensure_json_serializable(value: Any) -> Any:
    """
    Ensure the return value is a JSON object (dict) and JSON-serializable.
    If not, raise RuntimeError.
    """
    if value is None:
        raise RuntimeError("main() must return a JSON object, got None")

    if not isinstance(value, dict):
        raise RuntimeError(f"main() must return a JSON object (dict), got {type(value).__name__}")

    try:
        dumped = json.dumps(value)
        return json.loads(dumped)
    except TypeError as e:
        raise RuntimeError(f"Return value of main() is not JSON-serializable: {e}")



def run_user_main(script_path: str) -> Dict[str, Any]:
    """
    Execute the user script and call main(), capturing stdout.
    Returns a dict with 'result' and 'stdout'.
    Raises RuntimeError on any user-visible error.
    """
    stdout_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            ns = load_user_module(script_path)
            main_fn = ensure_main_callable(ns)
            result = main_fn()

        stdout_value = stdout_buffer.getvalue()
        json_result = ensure_json_serializable(result)

        return {
            "result": json_result,
            "stdout": stdout_value,
        }

    finally:
        stdout_buffer.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: sandbox_runner.py <script_path>", file=sys.stderr)
        sys.exit(1)

    script_path = sys.argv[1]

    try:
        payload = run_user_main(script_path)
        print(json.dumps(payload))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception:
        err_msg = "Internal error while executing script"
        print(err_msg, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
