#!/bin/bash

# Yufeed - GitHub Push Script
# This script will push your repository to GitHub

set -e  # Exit on any error

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║             Yufeed - GitHub Push Assistant                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -f "ARCHITECTURE.md" ]; then
    echo -e "${RED}❌ Error: Not in Yufeed directory${NC}"
    echo "Please run this script from the Yufeed project root"
    exit 1
fi

echo -e "${GREEN}✅ Found Yufeed project${NC}"
echo ""

# Step 1: Verify git status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Verifying Git Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}❌ Working tree is not clean!${NC}"
    echo "Please commit all changes before pushing"
    git status
    exit 1
fi

echo -e "${GREEN}✅ Working tree is clean${NC}"
echo ""

# Step 2: Check if remote exists
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Checking Remote Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if git remote get-url origin > /dev/null 2>&1; then
    CURRENT_REMOTE=$(git remote get-url origin)
    echo -e "${YELLOW}⚠️  Remote 'origin' already exists:${NC}"
    echo "   $CURRENT_REMOTE"
    echo ""
    read -p "Remove and re-add remote? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
        echo -e "${GREEN}✅ Removed existing remote${NC}"
    else
        echo "Keeping existing remote"
    fi
fi

# Step 3: Check if GitHub repo exists
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: GitHub Repository Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: You must create the GitHub repository first!${NC}"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: Yufeed"
echo "3. Description: EU Legal Monitoring & AML Compliance Platform"
echo "4. Visibility: Private (recommended) or Public"
echo "5. DO NOT check 'Initialize with README' or any other options"
echo "6. Click 'Create repository'"
echo ""
read -p "Have you created the GitHub repository? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Please create the repository first, then run this script again${NC}"
    exit 1
fi

# Step 4: Add remote
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Adding GitHub Remote"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REPO_URL="https://github.com/nadirimene-prog/Yufeed.git"

if ! git remote get-url origin > /dev/null 2>&1; then
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✅ Added remote: $REPO_URL${NC}"
else
    echo -e "${GREEN}✅ Remote already configured${NC}"
fi

echo ""
echo "Verifying remote:"
git remote -v

# Step 5: Show what will be pushed
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Review What Will Be Pushed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Recent commits:"
git log --oneline -6
echo ""

COMMIT_COUNT=$(git rev-list --count HEAD)
echo -e "${GREEN}Total commits to push: $COMMIT_COUNT${NC}"

# Final confirmation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6: Push to GitHub"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}⚠️  You will be prompted for GitHub credentials${NC}"
echo ""
echo "If you have 2FA enabled:"
echo "  - Username: nadirimene-prog"
echo "  - Password: Use a Personal Access Token (not your password!)"
echo "  - Get token at: https://github.com/settings/tokens"
echo ""
read -p "Ready to push? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Push cancelled. Run this script again when ready.${NC}"
    exit 0
fi

# Push!
echo ""
echo "Pushing to GitHub..."
echo ""

if git push -u origin main; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✅ SUCCESS! Repository pushed to GitHub!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🎉 Your repository is now live at:"
    echo "   https://github.com/nadirimene-prog/Yufeed"
    echo ""
    echo "Next steps:"
    echo "  1. Visit the repository and verify everything uploaded"
    echo "  2. Add repository topics (Settings → About → Topics)"
    echo "  3. Enable branch protection (Settings → Branches)"
    echo "  4. Configure Dependabot (Settings → Security)"
    echo "  5. Invite collaborators if needed"
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${RED}❌ Push failed!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Common issues:"
    echo "  1. Authentication failed - Check your credentials/token"
    echo "  2. Repository doesn't exist - Create it on GitHub first"
    echo "  3. Permission denied - Ensure you have write access"
    echo ""
    echo "See GITHUB_SETUP.md for troubleshooting help"
    exit 1
fi
