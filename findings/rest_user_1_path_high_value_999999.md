# Finding: path_high_value_999999

## Summary
- Generated: 2026-04-07T19:42:03.137554+00:00
- Severity: `informational`
- Endpoint: [[endpoints/rest_user_1]]
- Resource: [[resources/user]]

## Links
- [[resources/user]]
- [[endpoints/rest_user_1]]
- [[hypotheses/rest_user_1]]
- [[experiments/rest_user_1_path_high_value_999999]]
- [[index]]

## Details
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
      "error": "HTTPSConnectionPool(host='jsonplaceholder.typicode.com', port=443): Max retries exceeded with url: /rest/user/999999 (Caused by NewConnectionError(\"HTTPSConnection(host='jsonplaceholder.typicode.com', port=443): Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions\"))"
    },
    "elapsed_ms": 0,
    "headers": {},
    "status_code": 0,
    "url": "https://jsonplaceholder.typicode.com/rest/user/999999"
  },
  "endpoint": {
    "base_url": "https://jsonplaceholder.typicode.com",
    "body": {},
    "headers": {},
    "method": "GET",
    "params": {},
    "path": "/rest/user/1",
    "resource": "user",
    "source": "config"
  },
  "hypothesis": {
    "confidence": "medium",
    "confidence_score": 0.67,
    "hypothesis": "GET /rest/user/1 may allow access to high-value or sparse user identifiers without ownership checks. Prior related context: GET::/rest/user/1",
    "mutations": [
      {
        "body": {},
        "description": "Replace path identifier with a distant high value.",
        "headers": {},
        "name": "path_high_value_999999",
        "params": {},
        "path": "/rest/user/999999"
      }
    ],
    "name": "idor_sparse_identifier_enumeration",
    "resource_understanding": "The final path segments suggest a direct object lookup for 'user'.",
    "test_cases": [
      "Try a distant identifier such as 999999 and compare status code and response body size.",
      "Treat unchanged denial responses as not confirmed rather than positive findings."
    ]
  },
  "mutation": {
    "body": {},
    "description": "Replace path identifier with a distant high value.",
    "headers": {},
    "name": "path_high_value_999999",
    "params": {},
    "path": "/rest/user/999999"
  },
  "validation": {
    "baseline_size": 363,
    "baseline_status": 0,
    "body_changed": true,
    "candidate_size": 368,
    "candidate_status": 0,
    "data_leakage_detected": false,
    "decision": "Inconclusive",
    "hypothesis_name": "idor_sparse_identifier_enumeration",
    "is_interesting": false,
    "mutation_name": "path_high_value_999999",
    "new_leakage_patterns": [],
    "reasons": [
      "Transport failure prevented a reliable authorization comparison"
    ],
    "response_size_changed": false,
    "severity": "informational",
    "status_changed": false
  }
}
```
