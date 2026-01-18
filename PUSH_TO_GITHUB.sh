#!/bin/bash
# Script to push volleyball_analytics_v2 to GitHub
# Replace YOUR_USERNAME and REPOSITORY_NAME with your actual values

echo "🚀 Pushing to GitHub..."
echo ""
echo "Please make sure you've created the repository on GitHub first!"
echo "Go to: https://github.com/new"
echo ""
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your repository name (default: volleyball_analytics_v2): " REPO_NAME
REPO_NAME=${REPO_NAME:-volleyball_analytics_v2}

echo ""
echo "Adding remote repository..."
git remote add origin https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git 2>/dev/null || git remote set-url origin https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git

echo "Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Done! Your code should now be on GitHub."
echo "Visit: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
