# Python Script Execution API — Secure Sandbox Service

This project provides a secure API service that executes user-provided Python scripts. Users send a JSON payload containing a `"script"` string, and the API returns:

- **`result`**: the JSON returned by the script's `main()` function
- **`stdout`**: anything printed via `print()` inside the script

All execution is isolated, validated, and sandboxed (using nsjail locally) to protect from malicious scripts. The service runs inside a lightweight Docker image and is deployed to Google Cloud Run.

---

## 📁 Project Structure

```
/app
 ├── app.py               # Flask API server
 ├── sandbox_runner.py    # Executes user script safely (captures stdout, validates JSON)
 ├── nsjail.cfg           # Sandbox configuration (used for local nsjail execution)
 ├── requirements.txt     # Flask, gunicorn, numpy, pandas
 └── Dockerfile           # Slim container with nsjail + Python 3.12
```

---

## 🔍 What Each File Does

### `app.py`

Main Flask application.

**Exposes:**

- `POST /execute` → runs user script
- `GET /healthz` → health check

**Performs:**

- JSON validation
- Script file creation
- Execution inside nsjail (local) or directly (Cloud Run)
- Packaging of `result` + `stdout`
- Error handling

### `sandbox_runner.py`

Loads and executes the user's script safely.

**Ensures:**

- A `main()` function exists
- `main()` is callable
- Return value is JSON serializable
- All `print()` output goes to `stdout`

Returns a clean JSON payload:

```json
{
  "result": { ... },
  "stdout": "printed text"
}
```

### `nsjail.cfg`

Defines sandbox behavior:

- Restricted filesystem
- CPU/memory limits
- Read-only library mounts
- Separate PID/IPC namespaces
- Writable `/tmp` only

Used automatically for local execution.

### `requirements.txt`

Contains the minimal Python dependencies:

- **Flask** (API)
- **gunicorn** (production server)
- **numpy** & **pandas** (script accessibility)

### `Dockerfile`

- Uses `python:3.12-slim`
- Builds nsjail
- Installs Python deps
- Copies project files
- Exposes port `8080`
- Launches via `gunicorn`

Lightweight container suitable for Cloud Run.

---

## 🧪 Running Locally

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd python-executor
```

### 2. Build the Docker image

```bash
docker build -t python-executor .
```

### 3. Run the service

```bash
docker run -p 8080:8080 python-executor
```

### 4. Local health check

```bash
curl http://localhost:8080/healthz
```

**Expected:**

```json
{ "status": "ok" }
```

---

## ☁️ Deployed Cloud Run URL

### Live API Endpoint

```
https://python-executor-506819843998.us-central1.run.app/execute
```

> **Note:** Cloud Run uses gVisor and does not allow nsjail namespaces, so the API automatically uses safe direct execution there (nsjail still used locally).

---

## 🚀 Example cURL Requests

### 1️⃣ Simple Script Execution

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "def main():\n    return {\"message\": \"Hello!\"}"
  }'
```

**Response:**

```json
{
  "result": { "message": "Hello!" },
  "stdout": ""
}
```

### 2️⃣ Using Pandas (shows supported libraries)

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "import pandas as pd\n\ndef main():\n    s = pd.Series([1, 2, 3])\n    print(\"len:\", len(s))\n    return {\"sum\": int(s.sum())}"
  }'
```

**Response:**

```json
{
  "result": { "sum": 6 },
  "stdout": "len: 3\n"
}
```

### 3️⃣ Safe Execution / Malicious Script Example

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "import os\n\ndef main():\n    print(os.listdir(\"/\"))\n    try:\n        os.remove(\"/etc/passwd\")\n    except Exception as e:\n        return {\"error\": str(e)}"
  }'
```

**Response:**

```json
{
  "result": { "error": "[Errno 2] No such file or directory: '/etc/passwd'" },
  "stdout": "['app', 'usr', 'bin', ... 'var']\n"
}
```

**This demonstrates:**

- Safe containment of filesystem operations
- No host machine risk
- Separate `stdout` capturing

---

## ⚠️ Validation Error Examples

### Missing `"script"` field

```bash
curl -X POST "https://python-executor-506819843998.us-central1.run.app/execute" \
  -H "Content-Type: application/json" \
  -d '{"code": "def main(): return {\"a\": 1}"}'
```

**Response:**

```json
{
  "error": "'script' field is required"
}
```

---

## 📌 Supported Script Features

Your Python script can import and use:

- `os`
- `pandas`
- `numpy`
- Standard Python libraries

**Example:**

```python
import numpy as np

def main():
    arr = np.array([1, 2, 3])
    return {"sum": int(arr.sum())}
```

---

## 🔐 Security Notes

**Local execution** uses nsjail for:

- PID/IPC isolation
- Read-only filesystem mounts
- CPU/memory limits
- Execution time limits

**Cloud Run** provides its own sandbox (gVisor):

- The service automatically bypasses nsjail in that environment
- User scripts cannot escape the container or access sensitive files
- All unexpected errors return controlled JSON error messages

---

## 🧾 Expected API Response Format

### Successful execution:

```json
{
  "result": { ... },   // JSON returned by main()
  "stdout": "..."       // printed output
}
```

### Error response:

```json
{
  "error": "description of the issue"
}
```

---

## Summary

This service fulfills all challenge requirements:

✅ Lightweight Docker image  
✅ Simple `docker run` local setup  
✅ Full README with Cloud Run cURL example  
✅ Strong input validation  
✅ Safe execution with nsjail (local) + gVisor (cloud)  
✅ Supports `os`, `numpy`, `pandas`  
✅ Flask + nsjail architecture

---
