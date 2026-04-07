# Experiment Record

- Generated: 2026-04-07T18:47:24.262211+00:00
- Vault Root: C:\Users\Charan Rayudu\Documents\fun-projects\Aegis-Security-Research-System

```json
{
  "baseline": {
    "body": {
      "error": "HTTPSConnectionPool(host='jsonplaceholder.typicode.com', port=443): Max retries exceeded with url: /rest/user/1 (Caused by NewConnectionError(\"HTTPSConnection(host='jsonplaceholder.typicode.com', port=443): Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions\"))"
    },
    "elapsed_ms": 0,
    "headers": {},
    "status_code": 0,
    "url": "https://jsonplaceholder.typicode.com/rest/user/1"
  },
  "candidate": {
    "body": {
      "error": "HTTPSConnectionPool(host='jsonplaceholder.typicode.com', port=443): Max retries exceeded with url: /rest/user/1?user_id=999999 (Caused by NewConnectionError(\"HTTPSConnection(host='jsonplaceholder.typicode.com', port=443): Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions\"))"
    },
    "elapsed_ms": 0,
    "headers": {},
    "status_code": 0,
    "url": "https://jsonplaceholder.typicode.com/rest/user/1"
  },
  "endpoint": {
    "base_url": "https://jsonplaceholder.typicode.com",
    "body": {},
    "headers": {},
    "method": "GET",
    "params": {},
    "path": "/rest/user/1"
  },
  "hypothesis": {
    "hypothesis": "GET /rest/user/1 may expose weak authorization checks or inconsistent validation under malformed input.",
    "method": "GET",
    "mutations": [
      {
        "description": "Replay the request without authorization material.",
        "headers": {
          "Authorization": ""
        },
        "name": "unauthenticated_request",
        "params": {}
      },
      {
        "description": "Manipulate path-adjacent identifiers through params to probe access controls.",
        "headers": {},
        "name": "id_tampering",
        "params": {
          "user_id": 999999
        }
      },
      {
        "description": "Inject suspicious metacharacters to detect parser inconsistencies.",
        "headers": {
          "X-Research-Probe": "input-pollution"
        },
        "name": "input_pollution",
        "params": {
          "probe": "' OR '1'='1"
        }
      }
    ],
    "risk_summary": "Potential authorization, input handling, and response inconsistency issues.",
    "target": "/rest/user/1"
  },
  "mutation": {
    "description": "Manipulate path-adjacent identifiers through params to probe access controls.",
    "headers": {},
    "name": "id_tampering",
    "params": {
      "user_id": 999999
    }
  },
  "validation": {
    "baseline_status": 0,
    "body_changed": true,
    "candidate_status": 0,
    "headers_changed": false,
    "is_interesting": false,
    "mutation_name": "id_tampering",
    "reasons": [
      "Transport error prevented reliable comparison"
    ],
    "severity": "informational",
    "status_changed": false
  }
}
```
