# GitHub Contribution Guide

This guide will help you contribute to the project by working on issues and submitting pull requests. **Always work on existing issues first** - only create branches for new features if no relevant issues exist.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Working on Issues](#working-on-issues)
3. [Creating Branches](#creating-branches)
4. [Making Changes](#making-changes)
5. [Submitting Pull Requests](#submitting-pull-requests)
6. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

- Git installed on your computer
- GitHub account
- Access to the project repository

### Clone the Repository

```bash
git clone https://github.com/ORIGINAL_OWNER/ai-training.git
cd ai-training
```

## Working on Issues

### 1. Choose an Issue

- Go to the "Issues" tab on GitHub
- Look for issues labeled `good first issue` or `help wanted`
- Read the issue description and requirements
- Comment on the issue to let others know you're working on it

### 2. Pull the Latest Changes

```bash
git checkout main
git pull origin main
```

## Creating Branches

**Important**: Only create branches if there's no existing issue for what you want to work on. Always check for related issues first.

### Command Line

```bash
git checkout -b feature/issue-123-implement-stats-function
```

### GitHub UI

1. Go to main branch on GitHub
2. Click branch dropdown → type branch name → create
3. Pull locally: `git checkout your-branch-name`

### Branch Naming

- `feature/issue-123-description` - New features
- `fix/issue-456-description` - Bug fixes
- `docs/issue-789-description` - Documentation

## Making Changes

### 1. Implement Your Changes

- Follow the issue requirements
- Write clean, readable code
- Test your changes locally

### 2. Commit Your Changes

```bash
git add .
git commit -m "Implement get_team_stats function for issue #123

- Add pagination search logic
- Handle team not found cases
- Add error handling for API failures"
```

### 3. Push Your Branch

```bash
git push origin feature/issue-123-implement-stats-function
```

## Submitting Pull Requests

### GitHub UI (Recommended)

1. **Go to Pull Requests Tab**

   - Click "Pull requests" → "New pull request"

2. **Select Branches**

   - **Base**: `main` (target branch)
   - **Compare**: Your feature branch

3. **Fill Out PR Details**

   - **Title**: Clear, descriptive title
   - **Description**:

     ```markdown
     ## Description

     Implements the `get_team_stats` function to resolve issue #123.

     ## Changes Made

     - Added pagination search logic
     - Implemented error handling
     - Added team not found handling

     ## Related Issue

     Closes #123
     ```

4. **Submit the PR**
   - Click "Create pull request"

### GitHub UI Workflow (Alternative)

1. **Create Branch**: Go to main → branch dropdown → type name → create
2. **Edit Files**: Click pencil icon → make changes → commit
3. **Create PR**: Pull requests tab → New pull request → fill details

### VS Code UI Workflow

1. **Create Branch**

   - Click branch name in bottom-left corner
   - Click "Create new branch"
   - Type branch name: `feature/issue-123-description`

2. **Make Changes**

   - Edit files in VS Code
   - See changes in Source Control panel (Ctrl+Shift+G)

3. **Commit Changes**

   - Go to Source Control panel
   - Stage changes: Click "+" next to files
   - Add commit message in text box
   - Click "Commit" button

4. **Push Changes**

   - Click "Sync Changes" or "Push" button
   - Or use Command Palette (Ctrl+Shift+P) → "Git: Push"

5. **Pull Changes**
   - Click "Sync Changes" button
   - Or Command Palette → "Git: Pull"

## Best Practices

### Commit Messages

- Use present tense: "Add feature" not "Added feature"
- Reference issues: "Fix #123" or "Closes #123"

### Pull Request Guidelines

- **Clear descriptions** - Explain what and why
- **Reference issues** - Link to related issues
- **Test thoroughly** - Ensure your changes work

## Common Commands

### Command Line

```bash
# Check status
git status

# Switch branches
git checkout branch-name

# Create new branch
git checkout -b new-branch-name

# Pull latest changes
git pull origin main

# Push your changes
git push origin branch-name
```

### VS Code UI Alternatives

- **Check status**: Source Control panel (Ctrl+Shift+G)
- **Switch branches**: Click branch name in bottom-left → select branch
- **Create branch**: Click branch name → "Create new branch"
- **Pull changes**: Click "Sync Changes" button
- **Push changes**: Click "Sync Changes" or "Push" button
- **Stage files**: Click "+" next to files in Source Control panel
- **Commit**: Type message in Source Control panel → click "Commit"

## Troubleshooting

**"Your branch is behind"**

```bash
git pull origin main
git push origin your-branch
```

**"Nothing to commit"**

- Check if you've staged changes: `git add .`
- Check if files changed: `git status`

---

**Remember**: Always work on existing issues first. Only create branches for new features if no relevant issues exist!
