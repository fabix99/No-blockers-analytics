# 🔑 GitHub Setup Guide

## Creating a Personal Access Token

### Method 1: Direct Link (Easiest)

Go directly to: **https://github.com/settings/tokens**

### Method 2: Through Settings

1. Go to GitHub.com and sign in
2. Click your **profile picture** (top right)
3. Click **"Settings"**
4. Scroll down on the left sidebar
5. Look for:
   - **"Developer settings"** (at the bottom)
   - OR **"Access tokens"** (in some accounts)
6. Click **"Personal access tokens"**
7. Click **"Tokens (classic)"**

### Creating the Token

1. Click **"Generate new token"** → **"Generate new token (classic)"**
2. Name it: `Volleyball Dashboard`
3. Select expiration: **90 days** (or your preference)
4. **Check the box**: `repo` (Full control of private repositories)
5. Scroll down and click **"Generate token"**
6. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

---

## Pushing to GitHub

### Using Personal Access Token

Run these commands in your terminal:

```bash
cd "/path/to/volleyball_analytics_v2"
git push -u origin main
```

When prompted:
- **Username**: Your GitHub username
- **Password**: Paste your Personal Access Token (NOT your GitHub password)

The token will be saved in your keychain, so you won't need to enter it again.

---

## Alternative: Use GitHub Desktop (No Token Needed!)

If you can't find the tokens page, you can use **GitHub Desktop** instead:

1. Download: https://desktop.github.com/
2. Install and sign in with GitHub
3. File → Add Local Repository
4. Select your folder
5. Click "Publish repository"
6. Done! No token needed!

---

## Alternative: Use SSH Instead

For a more permanent solution without tokens:

### Generate SSH Key

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### Add to SSH Agent

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### Add to GitHub

1. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
2. Go to GitHub → Settings → SSH and GPG keys → New SSH key
3. Paste and save

### Update Remote URL

```bash
git remote set-url origin git@github.com:USERNAME/REPOSITORY.git
```

---

## Troubleshooting

### Can't Find Token Settings?

If you have a GitHub **organization account** or **enterprise account**, try:
- https://github.com/settings/personal-access-tokens/tokens

### Token Not Working?

- Make sure you selected the `repo` scope
- Check that the token hasn't expired
- Try generating a new token

### Permission Denied?

- Verify you're using the correct username
- Make sure you're pasting the token, not your password
- Check that you have access to the repository

