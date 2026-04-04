# Manual Google Setup For Local YouTube Publishing

## 1. Enable The YouTube Data API v3

1. Open Google Cloud Console.
2. Create or select the project you want to use for local development.
3. Go to `APIs & Services -> Library`.
4. Search for `YouTube Data API v3`.
5. Click `Enable`.

## 2. Configure The OAuth Consent Screen

1. Open `APIs & Services -> OAuth consent screen`.
2. Choose `External` for local development unless you already use an internal Workspace setup.
3. Fill in the app name, support email, and developer contact email.
4. Add the scopes your backend uses:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/youtube`
   - `https://www.googleapis.com/auth/youtube.upload`
5. Add your Google account as a test user if the app is still in testing mode.

## 3. Create OAuth Web Application Credentials

1. Open `APIs & Services -> Credentials`.
2. Click `Create Credentials -> OAuth client ID`.
3. Choose `Web application`.
4. Add these local JavaScript origins:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
5. Add this backend redirect URI:
   - `http://localhost:8000/api/v1/integrations/youtube/callback`
6. Save the client and copy the generated client ID and client secret.

## 4. Backend Environment Variables

Copy these values into `backend/.env`:

```env
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/integrations/youtube/callback
FRONTEND_URL=http://localhost:5173
YOUTUBE_SCOPES=openid,email,profile,https://www.googleapis.com/auth/youtube,https://www.googleapis.com/auth/youtube.upload
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+psycopg://reels:reels@localhost:5432/reels
```

## 5. Frontend Live Mode

Create `frontend/.env.local` with:

```env
VITE_API_MODE=live
VITE_API_URL=http://localhost:8000
```

## 6. Local Run Checklist

1. Start Postgres, Redis, MinIO, and Mailpit.
2. Run backend migrations.
3. Start the FastAPI app on `http://localhost:8000`.
4. Start the publishing worker queue and Celery beat.
5. Start the frontend on `http://localhost:5173`.
6. Open the app and connect a YouTube account from the `Publishing -> YouTube Accounts` page.

## Notes

- Do not use Google service accounts for YouTube uploads here. The implemented flow uses standard user OAuth with stored refresh tokens.
- The backend stores tokens encrypted at rest using the app encryption key.
- Scheduled YouTube publishes are created as `private` uploads with `publishAt` in UTC, which matches the YouTube Data API expectation.
