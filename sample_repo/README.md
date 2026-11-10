# Sample Authentication Service

Microservice responsible for token issuance, HMAC-SHA256 signature verification, password hashing, and role-based permissions.

## Architecture

- `auth_service/auth.py`: Token encoding/decoding and verification routines.
- `auth_service/models.py`: Data models and auth exception hierarchies.
- `tests/test_auth.py`: Pytest suite covering token lifecycle and access control.

## Running Tests

```bash
pytest tests/
```
