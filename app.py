import os
import json
import uuid
import tempfile
import subprocess
from typing import Dict, Any
from flask import Flask, request, jsonify

app = Flask(__name__)

MAX_SCRIPT_SIZE = 10_000
NSJAIL_CONFIG_PATH = "/app/nsjail.cfg"


class ScriptExecutionError(Exception):
    pass


def run_in_sandbox(script: str) -> Dict[str, Any]:
    """Run the user script inside nsjail and return {'result', 'stdout'}."""

    script_id = uuid.uuid4().hex
    script_path = f"/tmp/script_{script_id}.py"

    # Write user script into writable tmp
    with open(script_path, "w") as f:
        f.write(script)

    cmd = [

    "nsjail",
    "--config", NSJAIL_CONFIG_PATH,
    "--quiet",
    "--",
    "/usr/local/bin/python",
    "/runtime/sandbox_runner.py",
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

    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if stderr:
            raise ScriptExecutionError(stderr)
        raise ScriptExecutionError("Sandbox failed to run script")

    try:
        payload = json.loads(proc.stdout)
    except Exception:
        raise ScriptExecutionError("Sandbox output is not valid JSON")

    if not isinstance(payload, dict) or "result" not in payload or "stdout" not in payload:
        raise ScriptExecutionError("Sandbox output missing required fields")

    return payload


@app.route("/execute", methods=["POST"])
def execute_script():
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

    try:
        result = run_in_sandbox(script)
        return jsonify(result), 200
    except ScriptExecutionError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        app.logger.exception("Unexpected server error")
        return jsonify(error="Internal server error"), 500


@app.route("/healthz", methods=["GET"])
def health():
    return jsonify(status="ok"), 200


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        message="Service is running. Use POST /execute with {'script': 'def main(): ...'}"
    ), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
