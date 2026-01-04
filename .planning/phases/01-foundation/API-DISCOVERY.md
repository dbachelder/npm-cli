# NPM API Discovery

**Discovered:** 2026-01-04
**Source:** GitHub Discussion #3265, NPM source code inspection

## Authentication API

### Endpoint
```
POST /api/tokens
```

### Request Format
```json
{
  "identity": "user@example.com",
  "secret": "password"
}
```

### Response Format
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires": "2026-01-05T10:32:00.000Z"
}
```

### Token Usage
Include token in Authorization header for all authenticated requests:
```
Authorization: Bearer {token}
```

### Known Limitations
- Tokens expire in 24-48 hours by default unless expiry is explicitly set
- Long-lived tokens can be created (up to 999 years tested by community)
- NPM v2.12.3 and earlier have CORS misconfiguration vulnerability (CVE-2025-50579)

### Headers
Required headers for authentication request:
```
Content-Type: application/json; charset=UTF-8
```

## Notes

This is discovery documentation based on community reverse-engineering. The NPM API is completely undocumented - there is no official API documentation, and the Swagger schema is incomplete.

API endpoints are discovered through:
1. NPM source code inspection (backend/routes/api)
2. Browser DevTools network analysis
3. Built-in Audit Log feature
4. Community discussions and testing
