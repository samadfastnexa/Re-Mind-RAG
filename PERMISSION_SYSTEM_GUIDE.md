# Permission System for History Deletion

## Overview
The permission system allows admins to control which users can delete their conversation history. By default, all users have permission to delete history, but admins can revoke this for specific users.

## Features Implemented

### Backend Changes
1. **Database Schema**: Added `can_delete_history` column to users table
   - Type: BOOLEAN (default: TRUE/1)
   - Auto-migrates existing databases on startup

2. **API Endpoint**: `PUT /api/auth/users/{user_id}/permissions`
   - Query parameter: `can_delete_history` (true/false)
   - Admin access only
   - Location: `rag_system/app/main.py`

3. **User Service**: Updated all user queries to include permission field
   - Function: `update_user_permission(user_id, can_delete_history)`
   - Location: `rag_system/app/services/user_service.py`

### Frontend Changes
1. **Admin Panel**: Permission toggle in user management table
   - Location: `rag-web/components/UserManagement.tsx`
   - Toggle switch UI for each user
   - Calls API to update permission

2. **Chat Interface**: Permission checks for deletion
   - Location: `rag-web/components/ChatInterface.tsx`
   - Fetches current user on load
   - Hides delete buttons if user lacks permission
   - Shows alert if delete attempted without permission

## Testing the Permission System

### Step 1: Start the Backend
```powershell
cd f:\samad\chatobot\rag_system
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

**Important**: On first startup after this update, the database will auto-migrate to add the `can_delete_history` column to existing users (defaults to true).

### Step 2: Start the Frontend
```powershell
cd f:\samad\chatobot\rag-web
npm run dev
```

### Step 3: Test as Admin
1. Login as admin user
2. Navigate to Admin panel (http://localhost:3000/admin)
3. Click "Users" tab
4. You should see a "Delete History" column with toggle switches
5. Toggle OFF for a test user
6. Verify the toggle switches properly

### Step 4: Test as Regular User
1. Logout and login as the test user (whose permission was turned off)
2. Go to chat interface
3. Ask some questions to create conversation history
4. Click the History button (clock icon)
5. **Expected behavior**: Delete buttons should NOT be visible
6. If you somehow trigger delete (via console), you'll see an alert: "You do not have permission to delete conversation history."

### Step 5: Restore Permission
1. Login as admin again
2. Go to Admin → Users
3. Toggle ON the permission for the test user
4. Login as test user
5. **Expected behavior**: Delete buttons now visible in history sidebar

## Database Migration Details

The migration code in `user_service.py`:
```python
# Check if can_delete_history column exists
cursor.execute("PRAGMA table_info(users)")
columns = [column[1] for column in cursor.fetchall()]

if 'can_delete_history' not in columns:
    print("Migrating database: Adding can_delete_history column...")
    cursor.execute('ALTER TABLE users ADD COLUMN can_delete_history INTEGER DEFAULT 1')
    conn.commit()
```

## API Usage Examples

### Check Current User Permission
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response includes:
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "role": "user",
  "is_active": true,
  "can_delete_history": false,
  "created_at": "2024-01-01T00:00:00"
}
```

### Update User Permission (Admin Only)
```bash
curl -X PUT "http://localhost:8000/api/auth/users/2/permissions?can_delete_history=false" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## Files Modified

### Backend
- `rag_system/app/auth_models.py` - Added field to models
- `rag_system/app/services/user_service.py` - Database migration & permission function
- `rag_system/app/main.py` - New API endpoint

### Frontend
- `rag-web/lib/api.ts` - User interface & API method
- `rag-web/components/UserManagement.tsx` - Toggle UI
- `rag-web/components/ChatInterface.tsx` - Permission checks

## Troubleshooting

### Backend Issues
**Database migration doesn't run**
- Check console output on backend startup for migration message
- Verify `users.db` exists in `rag_system` directory
- Manual check: `sqlite3 users.db "PRAGMA table_info(users);"`

**Permission update fails**
- Verify logged in as admin user
- Check backend logs for error details
- Ensure user_id is valid

### Frontend Issues
**Toggle doesn't work**
- Check browser console for API errors
- Verify admin token is valid
- Check network tab for 401/403 errors

**Delete buttons still visible**
- Hard refresh the page (Ctrl+Shift+R)
- Check localStorage is enabled
- Verify `currentUser` state loaded properly

**Changes don't persist**
- Backend may have crashed during database write
- Check backend console for SQLite errors
- Verify database file permissions

## Default Behavior
- **New users**: `can_delete_history = true` (allowed)
- **Existing users after migration**: `can_delete_history = true` (allowed)
- **Admin users**: Can always manage permissions via admin panel
- **Regular users**: Cannot change their own or others' permissions

## Security Notes
- Only admins can modify user permissions
- Permission checks happen on both frontend (UI) and backend (logic)
- Frontend uses JWT token to authenticate API requests
- Backend validates admin role before allowing permission changes
