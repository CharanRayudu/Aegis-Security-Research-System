# Experiment Record

- Generated: 2026-04-07T18:55:05.663894+00:00
- Vault Root: C:\Users\Charan Rayudu\Documents\fun-projects\Aegis-Security-Research-System

```json
{
  "baseline": {
    "body": {
      "error": "HTTPSConnectionPool(host='jsonplaceholder.typicode.com', port=443): Max retries exceeded with url: /rest/user/2 (Caused by NewConnectionError(\"HTTPSConnection(host='jsonplaceholder.typicode.com', port=443): Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions\"))"
    },
    "elapsed_ms": 0,
    "headers": {},
    "status_code": 0,
    "url": "https://jsonplaceholder.typicode.com/rest/user/2"
  },
  "candidate": {
    "body": {
      "error": "HTTPSConnectionPool(host='jsonplaceholder.typicode.com', port=443): Max retries exceeded with url: /rest/user/2 (Caused by NewConnectionError(\"HTTPSConnection(host='jsonplaceholder.typicode.com', port=443): Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions\"))"
    },
    "elapsed_ms": 0,
    "headers": {},
    "status_code": 0,
    "url": "https://jsonplaceholder.typicode.com/rest/user/2"
  },
  "endpoint": {
    "base_url": "https://jsonplaceholder.typicode.com",
    "body": {},
    "headers": {},
    "method": "GET",
    "params": {},
    "path": "/rest/user/2",
    "source": "response_discovery"
  },
  "hypothesis": {
    "confidence": 0.86,
    "hypothesis": "GET /rest/user/2 may return data across identity boundaries when identifiers are modified.",
    "mutations": [
      {
        "body": {},
        "description": "Replay the request without authorization material.",
        "headers": {
          "Authorization": ""
        },
        "name": "unauthenticated_request",
        "params": {}
      },
      {
        "body": {},
        "description": "Inject role-oriented headers to probe trust in client claims.",
        "headers": {
          "X-Forwarded-User": "admin",
          "X-Original-User": "admin"
        },
        "name": "header_role_spoof",
        "params": {}
      }
    ],
    "name": "authorization_bypass",
    "risk_summary": "Access-control flaws often appear around direct object references."
  },
  "mutation": {
    "body": {},
    "description": "Inject role-oriented headers to probe trust in client claims.",
    "headers": {
      "X-Forwarded-User": "admin",
      "X-Original-User": "admin"
    },
    "name": "header_role_spoof",
    "params": {},
    "path": "/rest/user/2"
  },
  "validation": {
    "baseline_status": 0,
    "body_changed": false,
    "candidate_status": 0,
    "headers_changed": false,
    "hypothesis_name": "authorization_bypass",
    "is_interesting": false,
    "mutation_name": "header_role_spoof",
    "reasons": [
      "Transport error prevented reliable comparison"
    ],
    "severity": "informational",
    "status_changed": false
  }
}
```
