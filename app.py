import os
import json
import tempfile
import subprocess
from typing import Dict, Any

from flask import Flask, request, jsonify

app = Flask(__name__)

MAX_SCRIPT_SIZE = 10_000  # characters, basic protection
NSJAIL_CONFIG_PATH = "/app/nsjail.cfg"  # where the config lives inside the container


class ScriptExecutionError(Exception):
    pass


def run_in_sandbox(script_path: str) -> Dict[str, Any]:
    """
    Run sandbox_runner.py against the user script.
    If DISABLE_NSJAIL=true, run directly (for environments where nsjail is blocked, e.g. Cloud Run).
    Otherwise, run inside nsjail using nsjail.cfg.
    """
    disable_nsjail = os.getenv("DISABLE_NSJAIL", "false").lower() == "true"

    if disable_nsjail:
        # No nsjail: run sandbox_runner directly
        cmd = [
            "/usr/local/bin/python",
            "/app/sandbox_runner.py",
            script_path,
        ]
    else:
        # Default: run inside nsjail (for local + challenge requirement)
        cmd = [
            "nsjail",
            "--config", NSJAIL_CONFIG_PATH,
            "--env", "LD_LIBRARY_PATH=/usr/local/lib",
            "--",
            "/usr/local/bin/python",
            "/app/sandbox_runner.py",
            script_path,
        ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise ScriptExecutionError("Script exceeded time limit")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        app.logger.error("Sandbox stderr: %s", stderr)

        if stderr:
            lines = [line.strip() for line in stderr.splitlines() if line.strip()]
            user_lines = [line for line in lines if not line.startswith("[")]

            # If sandboxing is blocked by environment, surface a clearer message
            for line in lines:
                if "Operation not permitted" in line or "permission denied" in line:
                    raise ScriptExecutionError(
                        "Sandbox could not start due to environment restrictions."
                    )

            if user_lines:
                err_msg = user_lines[-1]
            else:
                err_msg = lines[-1]
        else:
            err_msg = "Script failed with non-zero exit code"

        raise ScriptExecutionError(err_msg)

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        app.logger.error("Failed to decode sandbox output as JSON: %r", proc.stdout)
        raise ScriptExecutionError("Failed to parse sandbox output as JSON")

    if not isinstance(payload, dict) or "result" not in payload or "stdout" not in payload:
        raise ScriptExecutionError("Sandbox output missing 'result' or 'stdout'")

    return payload


@app.route("/execute", methods=["POST"])
def execute_script():
    # Basic input validation
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Invalid JSON payload"), 400

    script = data.get("script")
    if script is None:
        return jsonify(error="'script' field is required"), 400

    if not isinstance(script, str):
        return jsonify(error="'script' must be a string"), 400

    script = script.strip()
    if not script:
        return jsonify(error="'script' must not be empty"), 400

    if len(script) > MAX_SCRIPT_SIZE:
        return jsonify(error="Script too large"), 400

    # Write script to a temporary file
    tmp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    )
    try:
        tmp_file.write(script)
        tmp_file.flush()
        tmp_file.close()
        script_path = tmp_file.name

        result = run_in_sandbox(script_path)

        return jsonify(
            result=result["result"],
            stdout=result["stdout"],
        ), 200

    except ScriptExecutionError as e:
        return jsonify(error=str(e)), 400
    except Exception:
        app.logger.exception("Unexpected error while executing script")
        return jsonify(error="Internal server error"), 500
    finally:
        try:
            os.unlink(tmp_file.name)
        except OSError:
            pass


@app.route("/healthz", methods=["GET"])
def health_check():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    # For local development; in Docker we use gunicorn
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
