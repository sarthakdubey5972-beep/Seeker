Seeker (Flask + SQLite)

Setup (Windows PowerShell)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Data is stored in `seeker.db` in the project root.

Email verification

Set Gmail app password env vars before running:

```powershell
$env:SEEKER_SMTP_USER="seekernetworkofficial@gmail.com"
$env:SEEKER_SMTP_PASS="<your-gmail-app-password>"
```

On signup we email a 6-digit OTP. Users must verify before login.

