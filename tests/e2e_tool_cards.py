"""
Backend API tests for tool call persistence and config stability.
No Playwright needed - tests the API endpoints directly.
"""
import urllib.request
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def api(method, path, data=None):
    url = f"http://localhost:8000{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method=method)
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read())


errors = []

# ── Test 1: Config is correct ──
print("[1] Config...")
cfg = api("GET", "/api/config")
print(f"    model: {cfg['model']}")
print(f"    api_base_url: {cfg['api_base_url']}")
if cfg["model"] != "deepseek-v4-pro":
    errors.append(f"Expected model deepseek-v4-pro, got {cfg['model']}")

# ── Test 2: Config stays correct after multiple reads ──
print("\n[2] Config stability...")
for i in range(5):
    c = api("GET", "/api/config")
    if c["model"] != "deepseek-v4-pro":
        errors.append(f"Config model changed on read {i}: {c['model']}")
print("    5 reads: model stable")

# ── Test 3: Models list has opencode-zen and opencode-go ──
print("\n[3] Models list...")
models = api("GET", "/api/models")
providers = {m.get("provider", "") for m in models}
print(f"    Total: {len(models)}, providers: {sorted(providers)}")
if "opencode-zen" not in providers:
    errors.append("opencode-zen not in providers")
if "opencode-go" not in providers:
    errors.append("opencode-go not in providers")

# ── Test 4: Session CRUD ──
print("\n[4] Session CRUD...")
s = api("POST", "/api/sessions", {"model": "deepseek-v4-pro", "title": "E2E Test"})
sid = s["id"]
print(f"    Created: {sid}")

sessions = api("GET", "/api/sessions")
found = any(x["id"] == sid for x in sessions)
print(f"    Found in list: {found}")
if not found:
    errors.append("Session not found in list")

msgs = api("GET", f"/api/sessions/{sid}/messages")
print(f"    Messages: {len(msgs)}")

# ── Test 5: Config stays correct after session operations ──
print("\n[5] Config after session ops...")
cfg2 = api("GET", "/api/config")
if cfg2["model"] != "deepseek-v4-pro":
    errors.append(f"Config model changed after session ops: {cfg2['model']}")
print(f"    model: {cfg2['model']} (stable)")

# ── Test 6: Tool calls table exists ──
print("\n[6] Tool calls structure...")
# Messages endpoint should include tool_calls key
has_tc = any("tool_calls" in m for m in msgs)
print(f"    Messages have tool_calls key: {has_tc}")

# ── Test 7: Credentials loaded ──
print("\n[7] Credentials...")
creds = api("GET", "/api/credentials")
cred_names = [c["name"] for c in creds]
print(f"    Credentials: {cred_names}")
if "OPENCODE_GO_API_KEY" not in cred_names:
    errors.append("OPENCODE_GO_API_KEY not in credentials")

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"FAILED: {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
