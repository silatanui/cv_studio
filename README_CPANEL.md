# cPanel & GitHub Deployment Guide — CV Studio (`tanuisila.dev/cv_studio`)

This guide explains how to deploy **CV Studio** to **cPanel** via **GitHub**, configured under the URL **`tanuisila.dev/cv_studio`** and the cPanel folder **`cv_studio`**, with **automated continuous deployment** so every push to GitHub immediately updates the live site.

---

## Architecture Overview

```
[ Local Development ] 
         │  git push origin main
         ▼
    [ GitHub ]
         │  cPanel Git Webhook OR GitHub Action
         ▼
[ cPanel /home/USER/cv_studio ]
   ├── passenger_wsgi.py (Phusion Passenger entrypoint)
   ├── wsgi_app.py (Synchronous WSGI with /cv_studio subpath support)
   ├── .cpanel.yml (Runs deployment tasks & touches tmp/restart.txt)
   └── tmp/restart.txt (Instructs Passenger to reload the Python app)
         │
         ▼
[ Live Web: https://tanuisila.dev/cv_studio ]
```

---

## 1. Local Git Setup (Push to GitHub)

1. Create a **new repository** on [GitHub](https://github.com/new) (e.g. `cv_studio`). Keep it public or private.
2. In your local terminal inside `c:\Users\silat\Desktop\Projects\cv_studio`, run:
   ```bash
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/cv_studio.git
   git add .
   git commit -m "Initial commit for cv_studio with cPanel deployment"
   git branch -M main
   git push -u origin main
   ```

---

## 2. Set Up Python App in cPanel

1. Log into your **cPanel** at `tanuisila.dev:2083` (or your host's cPanel login).
2. Under the **Software** section, click **Setup Python App**.
3. Click **Create Application**:
   - **Python version**: Choose `3.10` or `3.11` (or highest available).
   - **Application root**: `cv_studio` *(this creates `/home/YOUR_CPANEL_USER/cv_studio`)*.
   - **Application URL**: Select `tanuisila.dev` and enter `cv_studio` in the path box.
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
4. Click **Create** (top right).
5. At the top of the Python App page, copy the virtualenv command shown, for example:
   ```bash
   source /home/YOUR_CPANEL_USER/virtualenv/cv_studio/3.11/bin/activate && cd /home/YOUR_CPANEL_USER/cv_studio
   ```

---

## 3. Clone Repository in cPanel (Git™ Version Control)

1. In cPanel, go to the **Files** section and click **Git™ Version Control**.
2. Click **Create**:
   - **Clone URL**: `https://github.com/YOUR_GITHUB_USERNAME/cv_studio.git` *(if private, use SSH or personal access token)*.
   - **Repository Path**: `cv_studio` *(matches your Python app folder!)*.
   - **Repository Name**: `cv_studio`
3. Click **Create**.
4. Once cloned, click **Manage** on the `cv_studio` repository.
5. In the **Deploy HEAD Commit** tab, notice the deploy instructions and the cPanel webhook URL.

---

## 4. Enable Automatic Deployment (Push to Live)

### Method A: cPanel Webhook (Zero Maintenance)
Whenever you push to GitHub, GitHub notifies cPanel to pull the latest code and restart the Python app:

1. In cPanel **Git™ Version Control** $\rightarrow$ Click **Manage** on `cv_studio`.
2. Go to the **Deploy HEAD Commit** tab and copy your repository **Webhook URL** (or generate one).
3. Go to your repository on **GitHub** $\rightarrow$ **Settings** $\rightarrow$ **Webhooks** $\rightarrow$ **Add webhook**:
   - **Payload URL**: Paste the cPanel Webhook URL.
   - **Content type**: `application/json`
   - **Which events**: Select `Just the push event`.
   - Click **Add webhook**.
4. How it works:
   - When GitHub calls the webhook, cPanel runs `git pull`.
   - cPanel detects `.cpanel.yml` in your repo:
     ```yaml
     ---
     deployment:
       tasks:
         - export DEPLOYPATH=/home/$USER/cv_studio
         - if [ -d "$DEPLOYPATH" ] && [ "$PWD" != "$DEPLOYPATH" ]; then /bin/cp -R * $DEPLOYPATH; fi
         - /bin/mkdir -p $DEPLOYPATH/tmp
         - /bin/touch $DEPLOYPATH/tmp/restart.txt
     ```
   - Touching `tmp/restart.txt` causes Phusion Passenger to instantly reload your live app without server downtime.

### Method B: GitHub Actions (Alternative / Advanced)
The repository includes `.github/workflows/deploy.yml`. If you configure GitHub Secrets (`CPANEL_WEBHOOK_URL` or SSH secrets), pushing to `main` will automatically trigger the deployment workflow.

---

## 5. First-Time Server Configuration

After cloning the repository the first time on cPanel, complete these one-time steps:

### A. Install Python Packages
1. In cPanel, open **Terminal** (under the *Advanced* section).
2. Activate your virtual environment and install requirements:
   ```bash
   source /home/YOUR_CPANEL_USER/virtualenv/cv_studio/3.11/bin/activate && cd /home/YOUR_CPANEL_USER/cv_studio
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
*(Alternative: Inside cPanel "Setup Python App", type `requirements.txt` under Configuration files and click **Run Pip Install**)*.

### B. Configure `.env` Secrets
1. In cPanel **File Manager**, navigate into `/home/YOUR_CPANEL_USER/cv_studio`.
2. Make sure hidden files are visible (Settings in top right $\rightarrow$ check **Show Hidden Files**).
3. Create a file named `.env` (copy from `.env.example`):
   ```ini
   OPENAI_API_KEY=your-actual-openai-api-key-here
   DEFAULT_PARSE_MODEL=gpt-4o-mini
   DEFAULT_OPTIMIZE_MODEL=gpt-4o-mini
   ```

### C. Set Directory Permissions
Ensure Passenger can write generated files:
```bash
chmod 755 /home/YOUR_CPANEL_USER/cv_studio
chmod 775 /home/YOUR_CPANEL_USER/cv_studio/uploads /home/YOUR_CPANEL_USER/cv_studio/outputs /home/YOUR_CPANEL_USER/cv_studio/tmp
```

### D. Restart App & Verify
1. In cPanel **Setup Python App**, click **Restart** next to `cv_studio`.
2. Open your browser and navigate to:
   ```
   https://tanuisila.dev/cv_studio
   ```
3. Test optimizing a CV, creating a cover letter, or viewing saved applications.

---

## 6. Your Daily Workflow Going Forward

Once set up, you never need to touch cPanel again for code updates:

1. Make your code changes locally on your PC.
2. Commit and push:
   ```bash
   git add .
   git commit -m "Update feature or design"
   git push origin main
   ```
3. GitHub triggers the webhook $\rightarrow$ cPanel pulls the commit $\rightarrow$ `.cpanel.yml` touches `tmp/restart.txt` $\rightarrow$ Your changes are immediately live at `https://tanuisila.dev/cv_studio`!
