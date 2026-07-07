# Deploy DevTrack — Get a Public URL

Your GitHub repo **stores the code**. To get a **working app** that anyone can open in a browser, deploy it on **Render** (free).

**GitHub (code):** https://github.com/hassanziarak-png/devtrack  
**Live app (after deploy):** `https://devtrack-xxxx.onrender.com` ← share this URL with your team

---

## Step 1 — Upload new files to GitHub

Before deploying, add these new files to your repo (upload on GitHub website):

1. Open https://github.com/hassanziarak-png/devtrack
2. Click **Add file** → **Upload files**
3. Upload from `/Users/kared/Projects/devtrack/`:
   - `render.yaml`
   - `Procfile`
   - `requirements.txt` (updated — replace the old one)
   - `app/config.py` (updated)
   - `app/main.py` (updated)
4. Click **Commit changes**

---

## Step 2 — Create a Render account

1. Go to **https://render.com**
2. Click **Get Started for Free**
3. Choose **Sign up with GitHub**
4. Allow Render to access your GitHub account

---

## Step 3 — Deploy with Blueprint (easiest)

1. On Render dashboard, click **New +** (top right)
2. Click **Blueprint**
3. Connect repository: select **`hassanziarak-png/devtrack`**
4. Render reads `render.yaml` and shows:
   - **devtrack** (web service)
   - **devtrack-db** (PostgreSQL database)
5. Click **Apply**

Wait 5–10 minutes. Status will change to **Live**.

---

## Step 4 — Open your live app

1. Click the **devtrack** web service (not the database)
2. At the top you will see a URL like:

   ```
   https://devtrack.onrender.com
   ```

3. **Click that URL** — this is your working app
4. Share this link with managers and developers

### First login (auto-created on first deploy)

| Role | Email | Password |
|------|-------|----------|
| Manager | manager@devtrack.local | manager123 |
| Developer | dev1@devtrack.local | dev123 |

**Change these passwords immediately** via User Management.

---

## Manual deploy (if Blueprint does not appear)

### A) Create database first

1. **New +** → **PostgreSQL**
2. Name: `devtrack-db` → Plan: **Free** → **Create**
3. Open the database → copy **Internal Database URL**

### B) Create web service

1. **New +** → **Web Service**
2. Connect repo: `hassanziarak-png/devtrack`
3. Settings:

   | Field | Value |
   |-------|--------|
   | Name | devtrack |
   | Region | closest to you |
   | Branch | main |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Plan | Free |

4. **Environment** → Add variables:

   | Key | Value |
   |-----|--------|
   | `DATABASE_URL` | paste Internal Database URL from step A |
   | `SECRET_KEY` | any long random string |
   | `EMAIL_ENABLED` | `false` |

5. Click **Create Web Service**

---

## Step 5 — Enable email (optional, later)

1. Sign up at **https://www.brevo.com** (free, 300 emails/day)
2. Get SMTP credentials
3. On Render → your **devtrack** service → **Environment** → add:

   ```
   EMAIL_ENABLED=true
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USER=your-brevo-email
   SMTP_PASSWORD=your-brevo-smtp-key
   SMTP_FROM=devtrack@yourcompany.com
   ```

4. Service will redeploy automatically

---

## Important notes

| Topic | Detail |
|-------|--------|
| **Free tier sleep** | App sleeps after 15 min idle. First visit may take 30–60 sec to wake up. |
| **GitHub ≠ live app** | `github.com/hassanziarak-png/devtrack` is code only. Use the Render URL to use the app. |
| **Database** | Data is saved in PostgreSQL on Render — it persists across restarts. |
| **Updates** | Push/upload changes to GitHub → Render auto-redeploys. |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build failed | Check Render **Logs** tab for errors |
| Blank page | Wait for deploy to finish (status = Live) |
| Login fails | Wait 60 sec on first visit (cold start), try again |
| Database error | Ensure `DATABASE_URL` is set and `psycopg2-binary` is in requirements.txt |

---

## Quick reference

```
GitHub repo:     https://github.com/hassanziarak-png/devtrack
Render signup:   https://render.com
Live app URL:    shown on Render dashboard after deploy
API docs:        https://YOUR-APP.onrender.com/docs
```
