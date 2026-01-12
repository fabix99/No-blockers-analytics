# 🚀 Deployment Guide: Streamlit Cloud

This guide walks you through deploying the Volleyball Analytics Dashboard to Streamlit Cloud so your team can access it online without installing Python.

## Prerequisites

1. **GitHub Account** (free) - [Sign up here](https://github.com/signup)
2. **Streamlit Cloud Account** (free) - [Sign up here](https://share.streamlit.io/)

---

## Step 1: Prepare Your Repository

### 1.1 Initialize Git Repository (if not already done)

```bash
cd "/path/to/volleyball_analytics_v2"
git init
git add .
git commit -m "Initial commit - Volleyball Analytics Dashboard"
```

### 1.2 Create GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon in the top right → "New repository"
3. Name it (e.g., `volleyball-analytics-dashboard`)
4. Choose **Private** (important for access control)
5. **Don't** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 1.3 Push Your Code to GitHub

GitHub will show you commands. Run these in your terminal:

```bash
git remote add origin https://github.com/YOUR_USERNAME/volleyball-analytics-dashboard.git
git branch -M main
git push -u origin main
```

*(Replace `YOUR_USERNAME` with your GitHub username)*

---

## Step 2: Deploy to Streamlit Cloud

### 2.1 Sign Up for Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Click "Sign up" → "Continue with GitHub"
3. Authorize Streamlit Cloud to access your GitHub account

### 2.2 Deploy Your App

1. In Streamlit Cloud, click **"New app"**
2. Fill in the form:
   - **Repository**: Select your repository
   - **Branch**: `main`
   - **Main file path**: `Dashboard/streamlit_dashboard.py`
   - **App URL**: Choose a custom URL (e.g., `volleyball-analytics`)
3. Click **"Deploy"**

### 2.3 Wait for Deployment

- Streamlit will install dependencies from `requirements.txt`
- First deployment takes 2-3 minutes
- You'll see build logs in real-time
- Once complete, you'll get a URL like: `https://your-app-name.streamlit.app`

---

## Step 3: Set Up Access Control

### Option A: Private GitHub Repository (Recommended)

1. **Keep your GitHub repo private**
   - Go to your repository → Settings → General
   - Scroll to "Danger Zone" → "Change repository visibility" → "Make private"

2. **Add team members to GitHub**
   - Go to Settings → Collaborators → "Add people"
   - Add their GitHub usernames or emails
   - They'll need to accept the invitation

3. **Team members access Streamlit Cloud**
   - They sign up at share.streamlit.io with their GitHub account
   - They'll automatically see your app if they have access to the GitHub repo

### Option B: Password Protection (Simple)

Add password protection directly in your Streamlit app:

1. In Streamlit Cloud: Settings → Secrets → Add:
   ```toml
   [authentication]
   password = "your-secure-password-here"
   ```

2. The dashboard includes `Dashboard/streamlit_authentication.py` - see that file for setup instructions.

### Option C: Streamlit Cloud Authentication (Enterprise)

For stricter control, Streamlit Cloud offers authentication features:
- Available in Streamlit Cloud Teams/Enterprise plans
- Allows password protection
- User management through Streamlit Cloud

---

## Step 4: Streamlit Configuration (Optional)

Create `.streamlit/config.toml` for custom theming:

```toml
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#050d76"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

---

## Step 5: Share with Your Team

Once deployed:

1. **Share the URL** with your team: `https://your-app-name.streamlit.app`
2. **Share access instructions**:
   - If using private GitHub repo: They need to sign up with GitHub and request access
   - If using password: Share the password securely
3. **Team members can**:
   - Upload match data files
   - View all analytics
   - Use the Live Event Tracker
   - Download insights
   - No Python installation needed!

---

## Updating Your App

To update the deployed app:

1. Make changes to your code locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update dashboard"
   git push
   ```
3. Streamlit Cloud automatically redeploys (or click "Reboot app" in Streamlit Cloud)

---

## Troubleshooting

### Build Fails

1. **Check requirements.txt** - Make sure all dependencies are listed
2. **Check build logs** - Streamlit Cloud shows detailed error messages
3. **Common issues**:
   - Missing dependencies → Add to requirements.txt
   - Python version issues → Check Python version in logs
   - Import errors → Verify file paths are correct

### App Won't Load

1. **Check main file path** - Must be `Dashboard/streamlit_dashboard.py`
2. **Check file structure** - Ensure all files are committed to GitHub
3. **Check secrets** - If using authentication, verify secrets are set

### Access Issues

1. **Private repo** - Ensure team members are added as collaborators
2. **Password** - Verify password is set correctly in Streamlit Cloud secrets
3. **GitHub permissions** - Team members need to authorize Streamlit Cloud

---

## Security Best Practices

1. ✅ Keep repository **private**
2. ✅ Use strong passwords if using password protection
3. ✅ Don't commit sensitive data (use Streamlit secrets)
4. ✅ Regularly update dependencies
5. ✅ Review who has access to the repository

---

## Deployment Checklist

- [ ] Initialize Git repository
- [ ] Create GitHub repository (private)
- [ ] Push code to GitHub
- [ ] Deploy to Streamlit Cloud
- [ ] Set up access control
- [ ] Share with team
- [ ] Test deployment with sample data

---

## Support

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Community Forum](https://discuss.streamlit.io/)
- [GitHub Issues](https://github.com/streamlit/streamlit/issues)

