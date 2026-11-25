# CineVault (5GB chunk upload starter)

## Features
- Admin-only upload, edit/delete not exposed to visitors (delete protected)
- Admin login defaults: username `Ayush`, password `Ayush@12345`
- Browser uploads videos in 10MB chunks, designed to avoid large single-request body limits
- 5GB maximum per video (local server disk must have enough free space)
- Public library, title search, movie details, direct download
- Flask + HTML templates + CSS + JS, JSON metadata storage (no MySQL required for this starter)

## Run locally (Windows PowerShell)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ADMIN_USERNAME="Ayush"
$env:ADMIN_PASSWORD="Ayush@12345"
$env:SECRET_KEY="replace-with-a-long-random-secret"
python app.py
```
Visit http://127.0.0.1:5000 and admin at http://127.0.0.1:5000/admin/login.

## Upload limit
The app allows videos up to 5GB and uploads in 10MB pieces. The server's local disk needs enough space. This is NOT a cloud deployment solution. Vercel's serverless filesystem is ephemeral and request limits make it unsuitable for hosting/storing multi-GB media. For public deployment, host the frontend on Vercel, use a persistent backend and object storage (e.g. S3-compatible storage) with direct multipart upload, and configure credentials securely. Do not upload copyrighted movies unless you have distribution rights.

## Security before deployment
The default credentials are intentionally as requested for local use. Change them before exposing the site publicly. Replace SECRET_KEY. This starter uses a JSON metadata file and local storage, which is not intended for multi-instance production hosting. Add CSRF protection, rate limiting, secure session settings, and cloud storage authorization for production.
