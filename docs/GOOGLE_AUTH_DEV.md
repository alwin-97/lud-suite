# Google Auth Credentials (Development)

This project uses Django Allauth for Google login. For local development, you need
an OAuth 2.0 client ID and client secret from Google Cloud, then register them in
the Django admin as a Social Application.

## 1) Create OAuth credentials in Google Cloud

1. Go to https://console.cloud.google.com/ and create or select a project.
2. Navigate to "APIs & Services" -> "OAuth consent screen".
3. Set User Type to "External" (for local dev) and complete the required fields.
4. Navigate to "APIs & Services" -> "Credentials".
5. Click "Create Credentials" -> "OAuth client ID".
6. Application type: "Web application".
7. Authorized JavaScript origins:
   - http://localhost:8000
   - http://127.0.0.1:8000 (optional)
8. Authorized redirect URIs:
   - http://localhost:8000/accounts/google/login/callback/
   - http://127.0.0.1:8000/accounts/google/login/callback/ (optional)
9. Save and download the JSON file. Keep it locally as `client_secret_dev.json`.

Note: `client_secret_dev.json` is ignored by git (see `.gitignore`). Do not commit it.

## 2) Add the Social Application in Django

1. Start the server: `python .\manage.py runserver`.
2. Open the admin: http://localhost:8000/admin/
3. Go to "Sites" and ensure a Site exists for:
   - Domain: `localhost:8000`
   - Name: `localhost`
4. Go to "Social applications" -> "Add".
5. Provider: "Google".
6. Name: `Google (Dev)` (any name is fine).
7. Client id: copy `client_id` from the JSON file.
8. Secret key: copy `client_secret` from the JSON file.
9. Add the Site from step 3 to "Chosen sites".
10. Save.

## 3) Verify login

1. Visit the login page and click "Continue with Google".
2. If you see "Third-Party Login Failure", re-check:
   - Redirect URIs in Google Cloud match your local URL.
   - The Site domain in Django matches your local URL.
   - The correct client ID/secret were saved.

## Notes

- If you use a different port, update both the redirect URI in Google Cloud and the
  Site domain in Django.
- Allauth settings are already configured in `lud-suite/settings.py`.
