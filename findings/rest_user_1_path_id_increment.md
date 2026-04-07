# Finding Record

- Generated: 2026-04-07T18:54:22.628680+00:00
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
    "path": "/rest/user/1",
    "source": "config"
  },
  "hypothesis": {
    "confidence": 0.74,
    "hypothesis": "GET /rest/user/1 may allow object discovery when nearby identifiers are requested.",
    "mutations": [
      {
        "body": {},
        "description": "Request an adjacent identifier in the path when present.",
        "headers": {},
        "name": "path_id_increment",
        "params": {},
        "path": "/rest/user/2"
      }
    ],
    "name": "identifier_enumeration",
    "risk_summary": "Sequential identifiers can expose object enumeration or boundary conditions."
  },
  "mutation": {
    "body": {},
    "description": "Request an adjacent identifier in the path when present.",
    "headers": {},
    "name": "path_id_increment",
    "params": {},
    "path": "/rest/user/2"
  },
  "validation": {
    "baseline_status": 0,
    "body_changed": true,
    "candidate_status": 0,
    "headers_changed": false,
    "hypothesis_name": "identifier_enumeration",
    "is_interesting": false,
    "mutation_name": "path_id_increment",
    "reasons": [
      "Transport error prevented reliable comparison"
    ],
    "severity": "informational",
    "status_changed": false
  }
}
```
