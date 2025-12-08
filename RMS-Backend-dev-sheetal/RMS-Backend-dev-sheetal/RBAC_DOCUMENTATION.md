# Role-Based Access Control (RBAC) Implementation

## Overview

This system implements a hierarchical role-based access control system with three admin roles:

- **SUPER_ADMIN**: Full system access
- **ADMIN**: Can manage admins and HR
- **HR**: Can manage HR users only

## Role Hierarchy

```
SUPER_ADMIN (Highest)
    ↓
  ADMIN
    ↓
   HR (Lowest)
```

## Permissions Matrix

### Invite Users

| Caller Role   | Can Invite                    |
|---------------|-------------------------------|
| SUPER_ADMIN   | SUPER_ADMIN, ADMIN, HR        |
| ADMIN         | ADMIN, HR                     |
| HR            | HR only                       |

### View Admin List (`/v1/admins/list-all`)

| Caller Role   | Can See                       |
|---------------|-------------------------------|
| SUPER_ADMIN   | All users (SUPER_ADMIN, ADMIN, HR) |
| ADMIN         | ADMIN and HR                  |
| HR            | HR only                       |

### Edit Admin Details (`/v1/admins/update/{admin_id}`)

| Caller Role   | Can Edit                      |
|---------------|-------------------------------|
| SUPER_ADMIN   | Anyone                        |
| ADMIN         | ADMIN and HR                  |
| HR            | HR only                       |

### Delete Admins (`/v1/admins/delete-batch`)

| Caller Role   | Can Delete                    |
|---------------|-------------------------------|
| SUPER_ADMIN   | Anyone                        |
| ADMIN         | ADMIN and HR                  |
| HR            | HR only (excluding themselves)|

## API Endpoints

### Invite Admin
```http
POST /v1/admins/invite
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "new.admin@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "ADMIN"  // SUPER_ADMIN, ADMIN, or HR
}
```

**Response Codes:**
- `200 OK`: Invitation sent successfully
- `403 Forbidden`: Caller doesn't have permission to invite this role
- `409 Conflict`: User already exists

### List All Admins
```http
GET /v1/admins/list-all
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Admin list retrieved successfully.",
  "data": {
    "admins": [
      {
        "user_id": "uuid",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "role": "ADMIN",
        "created_at": "2025-01-01T00:00:00"
      }
    ]
  }
}
```

### Update Admin
```http
PUT /v1/admins/update/{admin_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "first_name": "Updated",
  "last_name": "Name",
  "new_email": "updated@example.com",
  "phone_number": "+0987654321"
}
```

**Response Codes:**
- `200 OK`: Update successful
- `403 Forbidden`: Caller doesn't have permission to edit this user
- `404 Not Found`: Admin user not found

### Delete Admins (Batch)
```http
DELETE /v1/admins/delete-batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response Codes:**
- `200 OK`: Deletion successful
- `403 Forbidden`: Caller doesn't have permission to delete these users
- `404 Not Found`: No matching admin accounts found

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(50),
    user_type VARCHAR(20) NOT NULL DEFAULT 'CANDIDATE',  -- ADMIN or CANDIDATE
    role VARCHAR(20) DEFAULT NULL,  -- SUPER_ADMIN, ADMIN, HR (NULL for CANDIDATE)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## JWT Token Structure

When a user authenticates, the JWT token includes:

```json
{
  "sub": "user_id",
  "role": "SUPER_ADMIN",  // or ADMIN, HR, CANDIDATE
  "fn": "First",
  "ln": "Last",
  "exp": 1234567890,
  "jti": "unique-token-id"
}
```

The `role` field in the JWT is used for authorization checks.

## Migration

To add the role column to an existing database:

```bash
# Run the migration
python scripts/add_role_column_migration.py

# Set the first super admin
python scripts/set_super_admin.py
```

Or manually:

```sql
-- Add role column
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT NULL;

-- Set existing admins to ADMIN role
UPDATE users SET role = 'ADMIN' WHERE user_type = 'ADMIN' AND role IS NULL;

-- Promote first admin to SUPER_ADMIN
UPDATE users SET role = 'SUPER_ADMIN' WHERE email = 'your-admin@example.com';
```

## Implementation Details

### Authorization Flow

1. **JWT Middleware** (`jwt_middleware.py`):
   - Validates JWT token
   - Extracts user payload (including role)
   - Sets `request.state.user` with user data
   - Checks `ROLE_PROTECTED_ENDPOINTS` for route-level access

2. **Controller** (e.g., `invite_admin_controller`):
   - Gets caller's role from `request.state.user`
   - Validates specific action permissions
   - Calls service layer with role information

3. **Service Layer** (e.g., `InviteAdminService`):
   - Performs business logic
   - Applies role-based filtering

4. **Repository Layer** (e.g., `get_all_admins_details`):
   - Executes database queries with role filters
   - Returns filtered results

### Protected Routes Configuration

In `protected_routes_config.py`:

```python
ROLE_PROTECTED_ENDPOINTS = {
    "/v1/admins/invite": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/admins/list-all": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/admins/update/{admin_id}": ["ADMIN", "SUPER_ADMIN"],
    "/v1/admins/delete-batch": ["SUPER_ADMIN", "ADMIN"],
    # ... more routes
}
```

This provides route-level access control. Fine-grained permissions are enforced in controllers/services.

## Error Handling

### Common Error Responses

**401 Unauthorized**
```json
{
  "success": false,
  "message": "Authentication required",
  "errors": []
}
```

**403 Forbidden**
```json
{
  "success": false,
  "message": "ADMIN can only invite ADMIN or HR roles",
  "errors": []
}
```

**404 Not Found**
```json
{
  "success": false,
  "message": "Admin user not found",
  "errors": []
}
```

## Security Considerations

1. **Token Security**: JWT tokens are stored in HTTP-only cookies
2. **Token Revocation**: JTI (JWT ID) is used for token blocklisting
3. **Role Validation**: Role is validated at multiple layers (middleware, controller, service, repository)
4. **Self-Protection**: HR users cannot delete themselves
5. **Audit Trail**: All admin actions should be logged (implement as needed)

## Testing

### Test Super Admin Permissions
```bash
# Login as super admin
curl -X POST http://localhost:8000/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "superadmin@example.com", "otp": "123456"}'

# Invite a new admin
curl -X POST http://localhost:8000/v1/admins/invite \
  -H "Cookie: access_token=<token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "first_name": "Admin", "role": "ADMIN"}'
```

### Test Admin Permissions
```bash
# Try to invite a super admin (should fail)
curl -X POST http://localhost:8000/v1/admins/invite \
  -H "Cookie: access_token=<admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "sa@example.com", "first_name": "SA", "role": "SUPER_ADMIN"}'
# Expected: 403 Forbidden
```

### Test HR Permissions
```bash
# Try to delete an admin (should fail)
curl -X DELETE http://localhost:8000/v1/admins/delete-batch \
  -H "Cookie: access_token=<hr-token>" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["admin-uuid"]}'
# Expected: 403 Forbidden or empty result
```

## Frontend Integration

When inviting users, the frontend should:

1. **Check caller's role** to show appropriate options
2. **Show role selector** based on permissions:
   - SUPER_ADMIN: Show all three options
   - ADMIN: Show ADMIN and HR
   - HR: Show HR only
3. **Handle errors gracefully** with user-friendly messages

Example React/TypeScript:

```typescript
const getRoleOptions = (userRole: string) => {
  if (userRole === 'SUPER_ADMIN') {
    return ['SUPER_ADMIN', 'ADMIN', 'HR'];
  } else if (userRole === 'ADMIN') {
    return ['ADMIN', 'HR'];
  } else if (userRole === 'HR') {
    return ['HR'];
  }
  return [];
};
```

## Troubleshooting

### 403 Forbidden on `/v1/admins/list-all`

**Cause**: User's token doesn't contain a valid `role` field.

**Solution**:
1. Check if user has a role: `SELECT email, user_type, role FROM users WHERE email = 'user@example.com'`
2. If role is NULL, update it: `UPDATE users SET role = 'ADMIN' WHERE email = 'user@example.com'`
3. User must log out and log in again to get a new token with the role

### Cannot invite SUPER_ADMIN

**Cause**: Only SUPER_ADMIN can invite other SUPER_ADMINs.

**Solution**: Login with a SUPER_ADMIN account to invite new super admins.

### Changes not reflected

**Cause**: JWT tokens are cached until they expire.

**Solution**: 
1. Logout and login again
2. Clear cookies
3. Wait for token expiration (default: 60 minutes for access token)

## Future Enhancements

1. **Audit Logging**: Log all admin actions (create, update, delete)
2. **Activity Dashboard**: Show recent admin activities
3. **Role Transitions**: Allow SUPER_ADMIN to promote/demote users
4. **Granular Permissions**: Add permission-level controls (read, write, delete)
5. **Multi-tenancy**: Support organization-level role hierarchies
6. **2FA**: Require two-factor authentication for SUPER_ADMIN actions

## Changelog

### Version 1.0.0 (2025-11-07)
- Initial RBAC implementation
- Added `role` column to users table
- Implemented hierarchical permissions (SUPER_ADMIN > ADMIN > HR)
- Updated invite, list, update, and delete endpoints
- Added role validation in middleware, controllers, services, and repositories
- Created migration scripts
