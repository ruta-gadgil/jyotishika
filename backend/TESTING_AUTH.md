# Testing Google OAuth Authentication

This guide explains how to test the Google OAuth authentication implementation.

## Prerequisites

1. **Set up Google OAuth credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable Google+ API
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
   - Copy the Client ID and Client Secret

2. **Configure environment variables:**
   - Add to your `local.env` file:
     ```
     GOOGLE_CLIENT_ID=your-client-id-here
     GOOGLE_CLIENT_SECRET=your-client-secret-here
     APP_BASE_URL=http://localhost:8000
     FRONTEND_BASE_URL=http://localhost:3000
     SECRET_KEY=your-random-secret-key-here
     ```

3. **Start the Flask server:**
   ```bash
   cd backend
   python -m flask run --port 8000
   # Or use your preferred method to start the server
   ```

## Automated Testing

Run the automated test script:

```bash
cd backend
python test_auth.py
```

This will test:
- Server health check
- `/me` endpoint when not logged in
- `/auth/logout` endpoint
- `/auth/google/login` redirect
- Callback error handling

## Manual Browser Testing

### 1. Test Login Flow

1. Open your browser and navigate to:
   ```
   http://localhost:8000/auth/google/login
   ```

2. You should be redirected to Google's login page.

3. Log in with your Google account and grant permissions.

4. After authentication, you'll be redirected to:
   ```
   http://localhost:3000?auth=success
   ```

### 2. Test Session Cookie

1. Open browser developer tools (F12 or Cmd+Option+I)

2. Go to **Application** tab (Chrome) or **Storage** tab (Firefox)

3. Check **Cookies** → `http://localhost:8000`

4. Verify that a `session_id` cookie exists with:
   - HttpOnly: ✓
   - Secure: ✗ (False for local development)
   - SameSite: Lax

### 3. Test `/me` Endpoint

**Using curl:**
```bash
# Save cookies from browser or use the session_id directly
curl http://localhost:8000/me \
  --cookie "session_id=YOUR_SESSION_ID_HERE"
```

**Expected response when logged in:**
```json
{
  "logged_in": true,
  "user": {
    "user_id": "123456789",
    "email": "user@example.com",
    "name": "John Doe",
    "picture": "https://..."
  }
}
```

**Expected response when not logged in:**
```json
{
  "logged_in": false
}
```

**Using browser:**
- Open: `http://localhost:8000/me`
- Check the Network tab in developer tools
- Verify the response contains your user info

### 4. Test Logout

**Using curl:**
```bash
curl -X POST http://localhost:8000/auth/logout \
  --cookie "session_id=YOUR_SESSION_ID_HERE"
```

**Expected response:**
```json
{
  "message": "Logged out successfully"
}
```

**Using browser:**
- Make a POST request to `http://localhost:8000/auth/logout`
- Or use a tool like Postman/Insomnia

### 5. Verify Session Cleared

After logout, test `/me` again:
```bash
curl http://localhost:8000/me \
  --cookie "session_id=YOUR_SESSION_ID_HERE"
```

Should return:
```json
{
  "logged_in": false
}
```

## Testing with Postman/Insomnia

### 1. Login Flow
- Create a GET request to `http://localhost:8000/auth/google/login`
- Check "Follow redirects" in settings
- Send request - you'll be redirected to Google

### 2. Get User Info
- Create a GET request to `http://localhost:8000/me`
- In the request, go to "Cookies" tab
- Add cookie: `session_id` = `YOUR_SESSION_ID`
- Send request

### 3. Logout
- Create a POST request to `http://localhost:8000/auth/logout`
- Add the `session_id` cookie
- Send request

## Testing Error Cases

### 1. Invalid State Token
```bash
curl "http://localhost:8000/auth/google/callback?code=test&state=invalid"
```

Expected: 400 Bad Request with `INVALID_STATE` error

### 2. Missing Authorization Code
```bash
curl "http://localhost:8000/auth/google/callback"
```

Expected: Redirect to frontend with error parameter

### 3. Missing Configuration
Temporarily remove `GOOGLE_CLIENT_ID` from environment:
```bash
curl http://localhost:8000/auth/google/login
```

Expected: 500 Internal Server Error with `CONFIGURATION_ERROR`

## Troubleshooting

### Issue: "Cannot connect to server"
- Make sure Flask is running on port 8000
- Check if another process is using port 8000

### Issue: "Redirect URI mismatch"
- Verify the redirect URI in Google Cloud Console matches exactly:
  `http://localhost:8000/auth/google/callback`
- Check `APP_BASE_URL` in your environment variables

### Issue: "Invalid client"
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
- Make sure you copied the full values without extra spaces

### Issue: Cookie not being set
- Check browser console for errors
- Verify CORS is configured correctly
- Make sure you're accessing from the correct origin

### Issue: Session not persisting
- Check that `SECRET_KEY` is set in environment
- Verify cookies are enabled in your browser
- Check browser console for cookie-related errors

## Next Steps

Once testing is complete:
1. Verify all endpoints work as expected
2. Test with different Google accounts
3. Test logout and session expiration
4. Consider adding session expiration logic
5. For production, update cookie settings (Secure=True, proper domain)

