from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta
import smtplib
import ssl
import random


DB_PATH = os.path.join(os.path.dirname(__file__), 'seeker.db')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            role TEXT CHECK(role IN ('company','individual')) NOT NULL DEFAULT 'individual',
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_verified INTEGER NOT NULL DEFAULT 0,
            otp_code TEXT,
            otp_expires_at TEXT
        );
        """
    )
    # Best-effort schema upgrade for verification columns
    try:
        conn.execute('ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0')
    except Exception:
        pass
    try:
        conn.execute('ALTER TABLE users ADD COLUMN otp_code TEXT')
    except Exception:
        pass
    try:
        conn.execute('ALTER TABLE users ADD COLUMN otp_expires_at TEXT')
    except Exception:
        pass
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            posted_at TEXT NOT NULL
        );
        """
    )
    # Best-effort schema upgrade to track poster user id
    try:
        conn.execute('ALTER TABLE jobs ADD COLUMN poster_user_id INTEGER')
    except Exception:
        pass
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            paid_at TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, job_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """
    )
    # Seed a few jobs if empty
    existing = conn.execute('SELECT COUNT(*) AS c FROM jobs').fetchone()['c']
    if existing == 0:
        seed_jobs = [
            ("Frontend Developer", "TechNova", "Remote", "Build modern web applications with React and TypeScript. 2+ years experience required.", datetime.utcnow().isoformat()),
            ("UI/UX Designer", "Designify", "Bangalore, India", "Design intuitive user interfaces for mobile and web. Portfolio required.", datetime.utcnow().isoformat()),
            ("Backend Engineer", "CloudCore", "San Francisco, CA", "Work on scalable APIs and cloud infrastructure. Experience with Node.js and AWS.", datetime.utcnow().isoformat()),
            ("Marketing Specialist", "MarketGenius", "Remote", "Drive digital marketing campaigns and analyze performance metrics. SEO/SEM skills a plus.", datetime.utcnow().isoformat()),
        ]
        conn.executemany('INSERT INTO jobs (title, company, location, description, posted_at) VALUES (?, ?, ?, ?, ?)', seed_jobs)
        conn.commit()
    conn.commit()
    conn.close()


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SEEKER_SECRET_KEY', 'dev-secret-change-me')
    app.config['SMTP_USER'] = os.environ.get('SEEKER_SMTP_USER', 'seekernetworkofficial@gmail.com')
    app.config['SMTP_PASS'] = os.environ.get('SEEKER_SMTP_PASS', '')
    app.config['EXTERNAL_BASE_URL'] = os.environ.get('SEEKER_BASE_URL', 'http://127.0.0.1:5000')

    # Ensure DB exists
    init_db()
    def generate_otp() -> str:
        return f"{random.randint(100000, 999999)}"

    def render_verification_email(otp: str) -> str:
        base = app.config['EXTERNAL_BASE_URL'].rstrip('/')
        logo_url = f"{base}/static/Seeker%20Logo.png"
        primary = "#0927eb"
        secondary = "#3a5bfa"
        return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Verify your email</title>
  </head>
  <body style="margin:0;padding:0;background:#f5f7ff;font-family:Segoe UI,Arial,sans-serif;color:#111;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7ff;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:16px;box-shadow:0 6px 28px rgba(9,39,235,0.12);overflow:hidden;">
            <tr>
              <td style="background:linear-gradient(90deg,{primary},{secondary});padding:20px 24px">
                <img src="{logo_url}" alt="Seeker" style="height:40px;display:block">
              </td>
            </tr>
            <tr>
              <td style="padding:28px 28px 8px 28px;">
                <h1 style="margin:0 0 8px 0;font-size:22px;color:#0b1a3a;">Verify your email</h1>
                <p style="margin:0;color:#445;line-height:1.5;">Use the one-time code below to verify your Seeker account. This code is valid for 10 minutes.</p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:8px 28px 24px 28px">
                <div style="font-size:32px;letter-spacing:6px;font-weight:800;color:{primary};background:#eef2ff;border:2px solid {secondary};border-radius:12px;padding:16px 24px;display:inline-block">{otp}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 24px 28px;">
                <a href="{base}/verify" style="display:inline-block;background:linear-gradient(90deg,{primary},{secondary});color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:600">Open verification page</a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 28px 28px;color:#667;">
                <p style="font-size:12px;line-height:1.6;margin:0">If you didn’t create a Seeker account, please ignore this email.</p>
              </td>
            </tr>
          </table>
          <div style="color:#99a; font-size:12px; margin-top:16px;">&copy; 2025 Seeker Media Private Limited</div>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    def send_email(to_email: str, subject: str, html_body: str) -> bool:
        smtp_user = app.config['SMTP_USER']
        smtp_pass = app.config['SMTP_PASS']
        if not smtp_user or not smtp_pass:
            return False
        headers = [
            f"From: Seeker <{smtp_user}>",
            f"To: <{to_email}>",
            f"Subject: {subject}",
            "MIME-Version: 1.0",
            "Content-Type: text/html; charset=UTF-8",
        ]
        msg = "\r\n".join(headers) + "\r\n\r\n" + html_body
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.encode('utf-8'))
            return True
        except Exception:
            return False

    @app.context_processor
    def inject_user():
        user = None
        if 'user_id' in session:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()
        return dict(current_user=user)

    @app.route('/')
    def home():
        conn = get_db_connection()
        jobs = conn.execute('SELECT * FROM jobs ORDER BY datetime(posted_at) DESC').fetchall()
        conn.close()
        return render_template('index.html', jobs=jobs)

    @app.get('/login')
    def login_get():
        return render_template('auth.html', mode='login')

    @app.post('/login')
    def login_post():
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('login_get'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login_get'))
        if not user['is_verified']:
            session['pending_verify_email'] = user['email']
            flash('Please verify your email to continue.', 'error')
            return redirect(url_for('verify_get'))
        session['user_id'] = user['id']
        flash('Signed in successfully.', 'success')
        return redirect(url_for('profile'))

    @app.get('/signup')
    def signup_get():
        return render_template('auth.html', mode='signup')

    @app.post('/signup')
    def signup_post():
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'individual')
        password = request.form.get('password', '')
        if role not in ('company', 'individual'):
            role = 'individual'
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'error')
            return redirect(url_for('signup_get'))
        conn = get_db_connection()
        otp = generate_otp()
        otp_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        try:
            conn.execute(
                'INSERT INTO users (name, email, phone, role, password_hash, created_at, is_verified, otp_code, otp_expires_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)',
                (name, email, phone, role, generate_password_hash(password), datetime.utcnow().isoformat(), otp, otp_expires)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Email is already registered.', 'error')
            conn.close()
            return redirect(url_for('signup_get'))
        # Send OTP email
        email_sent = send_email(
            to_email=email,
            subject='Verify your email · Seeker',
            html_body=render_verification_email(otp)
        )
        if not email_sent:
            flash('Could not send verification email. Please contact support.', 'error')
        conn.close()
        session['pending_verify_email'] = email
        flash('We have sent a 6-digit verification code to your email.', 'success')
        return redirect(url_for('verify_get'))

    @app.get('/logout')
    def logout():
        session.clear()
        flash('You have been signed out.', 'success')
        return redirect(url_for('home'))

    @app.get('/verify')
    def verify_get():
        if 'pending_verify_email' not in session and 'user_id' not in session:
            return redirect(url_for('home'))
        email = session.get('pending_verify_email')
        return render_template('verify.html', email=email)

    @app.post('/verify')
    def verify_post():
        code = request.form.get('code', '').strip()
        email = session.get('pending_verify_email')
        if not code or not email:
            flash('Invalid request.', 'error')
            return redirect(url_for('verify_get'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user:
            conn.close()
            flash('User not found.', 'error')
            return redirect(url_for('signup_get'))
        if not user['otp_code'] or code != user['otp_code']:
            conn.close()
            flash('Incorrect code.', 'error')
            return redirect(url_for('verify_get'))
        if user['otp_expires_at'] and datetime.utcnow() > datetime.fromisoformat(user['otp_expires_at']):
            conn.close()
            flash('Code expired. Please request a new one.', 'error')
            return redirect(url_for('verify_get'))
        conn.execute('UPDATE users SET is_verified = 1, otp_code = NULL, otp_expires_at = NULL WHERE id = ?', (user['id'],))
        conn.commit()
        conn.close()
        session.pop('pending_verify_email', None)
        session['user_id'] = user['id']
        flash('Email verified successfully.', 'success')
        # Redirect based on role
        if user['role'] == 'individual':
            return redirect(url_for('home'))
        return redirect(url_for('company_dashboard'))

    @app.post('/resend-otp')
    def resend_otp():
        email = session.get('pending_verify_email')
        if not email:
            return redirect(url_for('signup_get'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user:
            conn.close()
            flash('User not found.', 'error')
            return redirect(url_for('signup_get'))
        otp = generate_otp()
        otp_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        conn.execute('UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE id = ?', (otp, otp_expires, user['id']))
        conn.commit()
        conn.close()
        email_sent = send_email(
            to_email=email,
            subject='New verification code · Seeker',
            html_body=render_verification_email(otp)
        )
        if email_sent:
            flash('A new code has been sent to your email.', 'success')
        else:
            flash('Could not send email. Please check configuration.', 'error')
        return redirect(url_for('verify_get'))

    @app.get('/profile')
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login_get'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user and user['role'] == 'company':
            conn.close()
            return redirect(url_for('company_dashboard'))
        apps = conn.execute(
            'SELECT applications.*, jobs.title, jobs.company, jobs.location FROM applications JOIN jobs ON jobs.id = applications.job_id WHERE applications.user_id = ? ORDER BY datetime(applications.created_at) DESC',
            (session['user_id'],)
        ).fetchall()
        conn.close()
        return render_template('profile.html', applications=apps)

    @app.get('/company')
    def company_dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login_get'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or user['role'] != 'company':
            conn.close()
            return redirect(url_for('home'))
        jobs = conn.execute('SELECT * FROM jobs WHERE poster_user_id = ? ORDER BY datetime(posted_at) DESC', (session['user_id'],)).fetchall()
        conn.close()
        return render_template('company.html', company=user, jobs=jobs)

    @app.post('/company/jobs/new')
    def company_create_job():
        if 'user_id' not in session:
            return redirect(url_for('login_get'))
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        if not title or not location or not description:
            flash('All fields are required.', 'error')
            return redirect(url_for('company_dashboard'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or user['role'] != 'company':
            conn.close()
            return redirect(url_for('home'))
        conn.execute(
            'INSERT INTO jobs (title, company, location, description, posted_at, poster_user_id) VALUES (?, ?, ?, ?, ?, ?)',
            (title, user['name'], location, description, datetime.utcnow().isoformat(), session['user_id'])
        )
        conn.commit()
        conn.close()
        flash('Job posted successfully.', 'success')
        return redirect(url_for('company_dashboard'))

    @app.get('/jobs/<int:job_id>')
    def job_detail(job_id: int):
        conn = get_db_connection()
        job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        conn.close()
        if not job:
            abort(404)
        return render_template('job.html', job=job)

    @app.get('/jobs/<int:job_id>/apply')
    def job_apply(job_id: int):
        if 'user_id' not in session:
            return redirect(url_for('login_get'))
        conn = get_db_connection()
        job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        conn.close()
        if not job:
            abort(404)
        return render_template('payment.html', job=job)

    @app.post('/payment/<int:job_id>/confirm')
    def payment_confirm(job_id: int):
        if 'user_id' not in session:
            return redirect(url_for('login_get'))
        conn = get_db_connection()
        job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if not job:
            conn.close()
            abort(404)
        try:
            conn.execute(
                'INSERT OR IGNORE INTO applications (user_id, job_id, paid_at, created_at) VALUES (?, ?, ?, ?)',
                (session['user_id'], job_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            conn.commit()
        finally:
            conn.close()
        flash('Payment recorded. Application added to your profile.', 'success')
        return redirect(url_for('profile'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True)


