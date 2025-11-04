# 🚀 Push to GitHub - Step by Step

## Option 1: Use Personal Access Token (Recommended)

### Step 1: Create a Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Name it: `Volleyball Dashboard`
4. Select expiration: **90 days** (or your preference)
5. **Check the box**: `repo` (Full control of private repositories)
6. Scroll down and click **"Generate token"**
7. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

### Step 2: Push to GitHub

Run these commands in your terminal:

```bash
cd "/Users/fabiobarreto/Desktop/Cursor Folder/volleyball_analytics"
git push -u origin main
```

When prompted:
- **Username**: `fabix99`
- **Password**: Paste your Personal Access Token (NOT your GitHub password)

The token will be saved in your keychain, so you won't need to enter it again.

---

## Option 2: Use Token in URL (Quick but less secure)

If you want to avoid entering credentials each time:

```bash
cd "/Users/fabiobarreto/Desktop/Cursor Folder/volleyball_analytics"
git remote set-url origin https://YOUR_TOKEN@github.com/fabix99/No-blockers-analytics.git
git push -u origin main
```

Replace `YOUR_TOKEN` with your Personal Access Token.

---

## Option 3: Set up SSH (Best for long-term)

I can help you set up SSH keys if you prefer. This is the most secure option and doesn't require tokens.

---

## Quick Start

**Easiest way:**
1. Get token from: https://github.com/settings/tokens
2. Run: `git push -u origin main`
3. Enter username: `fabix99`
4. Enter password: (paste your token)

Done! ✅

