# PythonScript_ServiceSandbox

A secure, sandboxed Python script execution API that safely runs untrusted Python code in an isolated environment.

## Overview

PythonScript_ServiceSandbox is a Flask-based service that executes arbitrary Python scripts submitted via JSON API. All code runs in a hardened sandbox environment to ensure security and isolation.

**Key Features:**

- 🔒 Secure execution using nsjail (local) and gVisor (Cloud Run)
- 📤 Separate capture of JSON results and stdout output
- 🐍 Python 3.12 with pre-installed NumPy and Pandas
- ⚡ Production-ready with Gunicorn
- 🛡️ Multiple layers of validation and error handling

## Live Deployment

**Cloud Run URL:**

```
https://python-executor-506819843998.us-central1.run.app/execute
```

## How It Works

1. **Submit Code** - Send a Python script via POST request with a `main()` function
2. **Isolation** - Script is written to `/runtime/script.py` in an isolated environment
3. **Execution** - Code runs inside sandbox (nsjail locally, gVisor on Cloud Run)
4. **Output Collection** - Returns both JSON result from `main()` and all `print()` statements
5. **Validation** - Ensures code safety and proper return values

### Response Format

```json
{
  "result": {
    /* JSON returned by main() */
  },
  "stdout": "captured print output"
}
```

## Project Structure

```
/app
 ├── app.py              # Flask API (POST /execute, GET /healthz)
 ├── sandbox_runner.py   # Code validation, execution, and output capture
 ├── nsjail.cfg          # Sandbox configuration (local development)
 ├── requirements.txt    # Dependencies: Flask, gunicorn, numpy, pandas
 └── Dockerfile          # Container image with Python 3.12 + nsjail

/runtime                 # Writable directory for sandboxed processes
```

## API Endpoints

### `POST /execute`

Execute a Python script in the sandbox.

**Request Body:**

```json
{
  "script": "def main():\n    return {\"x\": 1}"
}
```

**Response:**

```json
{
  "result": { "x": 1 },
  "stdout": ""
}
```

### `GET /healthz`

Health check endpoint.

**Response:**

```json
{
  "status": "ok"
}
```

## Security Features

### Sandbox Configuration (Local - nsjail)

- Read-only root filesystem
- Isolated PID and IPC namespaces
- Writable `/tmp` only
- Memory and CPU limits enforced
- No device access
- Network isolation

### Cloud Run Security

- gVisor provides VM-level isolation
- Syscall filtering and interception
- Automatic security hardening
- IP-level isolation

## Running Locally

### Prerequisites

- Docker installed

### Build and Run

```bash
# Build the Docker image
docker build -t python-executor .

# Run the container
docker run -p 8080:8080 python-executor

# Test the health endpoint
curl http://localhost:8080/healthz
```

Expected response: `{"status": "ok"}`

## Example Usage

### 1. Basic Script Execution

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script":"def main():\n    return {\"status\": \"success\"}"}'
```

**Response:**

```json
{
  "result": { "status": "success" },
  "stdout": ""
}
```

### 2. Script with Print Statements

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    print(\"Processing data...\")\n    return {\"done\": True}"}'
```

**Response:**

```json
{
  "result": { "done": true },
  "stdout": "Processing data...\n"
}
```

### 3. Using NumPy and Pandas

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "import pandas as pd\nimport numpy as np\n\ndef main():\n    arr = np.array([1, 2, 3, 4, 5])\n    s = pd.Series(arr)\n    print(f\"Series length: {len(s)}\")\n    return {\"sum\": int(s.sum()), \"mean\": float(s.mean())}"
  }'
```

**Response:**

```json
{
  "result": { "sum": 15, "mean": 3.0 },
  "stdout": "Series length: 5\n"
}
```

### 4. Security Test - File System Access

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "import os\n\ndef main():\n    try:\n        os.remove(\"/etc/passwd\")\n        return {\"status\": \"removed\"}\n    except Exception as e:\n        return {\"error\": str(e)}"
  }'
```

**Response:**

```json
{
  "result": { "error": "[Errno 13] Permission denied: '/etc/passwd'" },
  "stdout": ""
}
```

✅ **Sandbox successfully prevents unauthorized file access**

## Comprehensive Test Cases

Below are real test cases with actual inputs and outputs from the service:

### Test 1: Simple Success Response

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n return {\"cloud\": \"ok\"}"}'
```

**Output:**

```json
{ "result": { "cloud": "ok" }, "stdout": "" }
```

---

### Test 2: Script with Print Statement

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n print(\"inside main\")\n return {\"ok\": True}"}'
```

**Output:**

```json
{ "result": { "ok": true }, "stdout": "inside main\n" }
```

---

### Test 3: NumPy and Pandas Operations

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "import pandas as pd, numpy as np\n\ndef main():\n arr = np.array([1,2,3])\n s = pd.Series(arr)\n print(\"len:\", len(s))\n return {\"sum\": int(s.sum())}"}'
```

**Output:**

```json
{ "result": { "sum": 6 }, "stdout": "len: 3\n" }
```

---

### Test 4: Missing 'script' Field

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"code": "def main(): return {\"a\": 1}"}'
```

**Output:**

```json
{ "error": "'script' field is required" }
```

---

### Test 5: Empty Script

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": ""}'
```

**Output:**

```json
{ "error": "'script' must not be empty" }
```

---

### Test 6: Missing main() Function

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def foo():\n return {\"x\": 1}"}'
```

**Output:**

```json
{
  "error": "[W][2025-11-25T04:57:33+0000][13] initNs():228 prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL): Invalid argument\nScript must define a function main()"
}
```

---

### Test 7: main() Returns Non-Dict

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n return 123"}'
```

**Output:**

```json
{
  "error": "[W][2025-11-25T04:57:54+0000][15] initNs():228 prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL): Invalid argument\nmain() must return a JSON object (dict)"
}
```

---

### Test 8: Non-Serializable Return Value (Set)

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n return {\"s\": {1,2,3}}"}'
```

**Output:**

```json
{
  "error": "[W][2025-11-25T04:58:07+0000][17] initNs():228 prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL): Invalid argument\nReturn value is not JSON-serializable: Object of type set is not JSON serializable"
}
```

---

### Test 9: File System Security - Unauthorized Delete

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "import os\n\ndef main():\n try:\n os.remove(\"/etc/passwd\")\n except Exception as e:\n return {\"error\": str(e)}"}'
```

**Output:**

```json
{
  "result": { "error": "[Errno 13] Permission denied: '/etc/passwd'" },
  "stdout": ""
}
```

✅ **Sandbox blocks unauthorized file deletion**

---

### Test 10: File System Security - Secrets Access

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "import os\n\ndef main():\n try:\n return {\"files\": os.listdir(\"/var/run/secrets\")}\n except Exception as e:\n return {\"error\": str(e)}"}'
```

**Output:**

```json
{
  "result": {
    "error": "[Errno 2] No such file or directory: '/var/run/secrets'"
  },
  "stdout": ""
}
```

✅ **Sandbox prevents access to sensitive directories**

---

### Test 11: Infinite Loop / Timeout

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n while True:\n pass\n return {\"done\": True}"}'
```

**Output:**

```json
{
  "error": "[W][2025-11-25T04:58:45+0000][23] initNs():228 prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL): Invalid argument"
}
```

✅ **Sandbox terminates long-running scripts**

---

### Test 12: List Accessible Directory

**Input:**

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"script": "import os\n\ndef main():\n return {\"files\": os.listdir(\"/app\")}"}'
```

**Output:**

```json
{
  "result": { "files": ["app.py", "nsjail.cfg", "requirements.txt"] },
  "stdout": ""
}
```

✅ **Scripts can read from /app directory**

## Error Handling

The API validates all inputs and handles errors gracefully:

| Error Case             | Response                                                  |
| ---------------------- | --------------------------------------------------------- |
| Missing `script` field | `{"error": "'script' field is required"}`                 |
| Empty script           | `{"error": "'script' must not be empty"}`                 |
| No `main()` function   | `{"error": "Script must define a function main()"}`       |
| Non-JSON return value  | `{"error": "Return value is not JSON-serializable: ..."}` |
| Execution timeout      | `{"error": "Sandbox failed to run script"}`               |
| Runtime exception      | `{"error": "Script execution failed: ..."}`               |

## Code Requirements

Your script must:

1. Define a `main()` function
2. Return a JSON-serializable object (dict, list, str, int, float, bool, None)
3. Not use the following return types: `set`, `bytes`, custom objects

**Valid return types:**

- `dict`, `list`, `str`, `int`, `float`, `bool`, `None`
- Nested combinations of the above

**Example:**

```python
def main():
    # This works ✓
    return {
        "data": [1, 2, 3],
        "status": "complete",
        "count": 42
    }
```

## Dependencies

- Python 3.12
- Flask
- Gunicorn
- NumPy
- Pandas
- nsjail
