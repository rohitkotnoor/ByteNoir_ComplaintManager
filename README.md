# College Complaint Management System

This Django web application lets students submit and track campus complaints and lets authorized administrators review, prioritize, and respond to them. It uses Django templates, SQLite, and a custom responsive interface.

## Features

### Students

- Register with a student account and sign in using Django authentication.
- Register using the College Register Number created by the college.
- Submit concerns in ten campus categories, including classrooms, hostel, Wi-Fi, and mess / food, and receive an automatic `CC-` reference number.
- Attach up to five JPG, PNG, WebP, or PDF files (10 MB each), suggest a priority, and choose anonymous reporting. Anonymous reports remain linked to the student's account for tracking, while administrators see no reporter identity.
- View only complaints they submitted, open their timeline, and read official responses.
- Receive in-app notifications when a case is assigned, its status or response changes, or it is escalated.
- Edit complaint details and add attachments while a complaint remains in **Submitted** status.
- Track every recorded status transition and who made it.

### Administrators

- Use an authorized staff account to view the campus complaint queue and live statistics.
- New complaints are routed to a department based on category. Administrators can assign a case to a different department or administrator.
- Search by reference, title, description, or visible student name; filter by status, category, priority, department, escalation, and date.
- Update complaint status, priority, assignment, and official response. Status and assignment changes are recorded in the audit history.
- Review student contact and profile information on identified complaints; anonymous reports conceal that information.
- Open attachments through authenticated downloads; anonymous reports conceal the reporter's identity in the complaint queue and detail pages.
- Open unresolved complaints are escalated after 48 hours by default, raised to urgent priority, and sent as in-app notifications to administrators and the reporting student.

## Technology

- Python 3.10 or newer
- Django 5.2
- SQLite
- HTML, custom CSS, and a small JavaScript enhancement for mobile navigation

No separate frontend framework or paid service is used.

## Project structure

```text
config/                 Django settings and project URLs
accounts/               Registration, profiles, authentication, role checks
complaints/              Complaint models, forms, permissions, and views
templates/               Shared layout and page templates
  accounts/
  complaints/
  errors/
static/css/site.css      Responsive visual styles
static/js/site.js        Mobile navigation control
static/images/           Reserved for local image assets
manage.py
requirements.txt
```

## Windows setup (PowerShell)

Open the project folder in VS Code and run these commands in its terminal, one at a time:

For local development, explicitly enable debug mode in this terminal before running Django commands:

```powershell
$env:DJANGO_DEBUG = "1"
```

1. Confirm Python is available:

   ```powershell
   python --version
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   if (Test-Path .\.venv\Scripts\Activate.ps1) { .\.venv\Scripts\Activate.ps1 } else { .\.venv\bin\Activate.ps1 }
   ```

   If PowerShell blocks activation for this terminal, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

3. Install Django:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Apply the database migrations:

   ```powershell
   python manage.py migrate
   ```

5. Create the first administrator interactively. Choose your own username and password when prompted:

   ```powershell
   python manage.py createsuperuser
   ```

   Django's user-created signal assigns a newly created superuser the administrator profile role. Do not add real credentials to source code.

6. Start the local server, bound to this computer only:

   ```powershell
   python manage.py runserver 127.0.0.1:8000
   ```

7. Open **http://127.0.0.1:8000/** in your browser. The Django administration site is at **http://127.0.0.1:8000/django-admin/**.

## Using the application

- Students choose **Register as a student** from the home page, create an account, then choose **Submit a complaint**. Their dashboard and **My complaints** show only their own reports.
- Sign-in throttles repeated failures by account and account/source-IP pair. After repeated failures, wait 15 minutes before trying again.
- New passwords must be at least 12 characters and pass Django's common-password and user-similarity checks.
- Administrators can choose **Register as an administrator** to submit an access request. The account stays inactive until an existing superuser approves it in Django Admin by activating the user, enabling Staff status, and granting the complaint view and change permissions. After approval, sign in through **Login as administrator**.
- Administrator access requires a superuser account or an authorized staff account. The first administrator must still be created with `python manage.py createsuperuser` so there is an existing account that can approve later requests.
- A staff user can be authorized by a superuser through Django Admin: create or select the user, mark **Staff status**, set that user's Profile role to **Administrator**, and grant the `complaints | complaint | Can view complaint` and `Can change complaint` permissions. Superusers always have administrator access.
- Logout is a CSRF-protected POST action.
- Students must sign in to use anonymous reporting so they can still track the case; the application hides their profile and original file names from complaint administrators. Report text or attachment contents can still identify the sender if students include identifying details.
- To escalate overdue cases even when no administrator is browsing the site, schedule `python manage.py escalate_complaints` to run hourly with Windows Task Scheduler or cron. The admin dashboard also processes overdue cases when opened.
- Set `COMPLAINT_ESCALATION_HOURS` to change the 48-hour escalation window.

## Run automated tests

```powershell
python manage.py test
```

Tests cover registration and login, complaint input validation and submission, ownership restrictions, student access to administrator pages, status and priority updates, status history, and missing references.

## Common issues

- **`No module named django`**: activate `.venv` and run `python -m pip install -r requirements.txt`.
- **PowerShell will not activate the environment**: run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.
- **Database table does not exist**: run `python manage.py migrate` from the project folder.
- **An account cannot open the admin dashboard**: confirm the account is a superuser, or that it has Staff status and Profile role **Administrator**.
- **Port 8000 is already in use**: run `python manage.py runserver 8001` and open `http://127.0.0.1:8001/`.

## Configuration and production notes

The app defaults to production-safe settings: debug is off, and startup requires a secret key and explicit allowed hostnames. For local development, set `DJANGO_DEBUG=1` in the terminal as shown above; a temporary random secret is generated for that process.

Before production deployment:

- Set `DJANGO_DEBUG=0`, store a strong `DJANGO_SECRET_KEY` in the hosting provider's secret manager, and set `DJANGO_ALLOWED_HOSTS` to exact hostnames without schemes or paths.
- Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the exact HTTPS origins when needed, such as `https://complaints.example.edu`.
- Serve the app over HTTPS. Production redirects to HTTPS, sets secure session and CSRF cookies, and enables HSTS. If TLS ends at a trusted reverse proxy that overwrites `X-Forwarded-Proto`, set `DJANGO_TRUST_PROXY_SSL_HEADER=1` so Django can detect HTTPS correctly; never enable it when clients can supply that header directly.
- Keep uploaded complaint files private. Do not configure the web server to serve `MEDIA_ROOT` or `/media/` publicly; users should access attachments only through the authenticated download view.
- Configure request rate limits at the reverse proxy or hosting edge as another layer against distributed login attempts. The built-in sign-in throttle limits repeated failures by account and account/source-IP pair.
- Configure a production database, backups, and private file storage. The built-in Django development server is for local use only.
