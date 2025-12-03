# Sample Test Data for User Registration System

## Valid Registration Data

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure123"
}
```

```json
{
  "username": "alice",
  "email": "Alice@Gmail.com",
  "password": "password456"
}
```

## Invalid Data (Should be rejected with 400)

### Missing Email
```json
{
  "username": "testuser",
  "password": "password123"
}
```

### Null Email (🐛 Currently returns 500, should return 400)
```json
{
  "username": "testuser",
  "email": null,
  "password": "password123"
}
```

### Empty Email
```json
{
  "username": "testuser",
  "email": "",
  "password": "password123"
}
```

### Invalid Email Format
```json
{
  "username": "testuser",
  "email": "not-an-email",
  "password": "password123"
}
```

### Short Password
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "123"
}
```

### Missing Username
```json
{
  "email": "test@example.com",
  "password": "password123"
}
```
