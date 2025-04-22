# Git Repository Setup

This document provides instructions for setting up VectorVault as a git repository and making the initial commit.

## Initializing the Repository

If you're starting from scratch:

```bash
# Initialize the git repository
git init

# Add all files to staging
git add .

# Create the initial commit
git commit -m "Initial commit of VectorVault - AI-powered document search engine"
```

## Creating a Branch

It's a good practice to create a feature branch for development:

```bash
# Create and switch to a new branch
git checkout -b feature/initial-setup

# Make changes...

# Commit your changes
git add .
git commit -m "Complete initial setup of VectorVault"
```

## Pushing to GitHub

To push your repository to GitHub:

1. [Create a new repository on GitHub](https://github.com/new) without initializing it with README, license, or .gitignore files.

2. Add the remote repository and push your code:

```bash
# Add the GitHub repository as a remote
git remote add origin https://github.com/yourusername/vectorvault.git

# Push your code to GitHub
git push -u origin feature/initial-setup
```

3. Create a pull request on GitHub to merge your feature branch into the main branch.

## Recommended Git Workflow

For future development:

1. Create feature branches for new features or bug fixes
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. Make changes and commit frequently with descriptive messages
   ```bash
   git add .
   git commit -m "Add specific feature or fix"
   ```

3. Push your branch to GitHub
   ```bash
   git push -u origin feature/new-feature-name
   ```

4. Create a pull request and merge after review

## .gitignore

We've already set up a `.gitignore` file that excludes:

- Virtual environment folders
- Python cache files
- Environment variables (.env)
- Generated FAISS index and document metadata
- IDE-specific files
- OS-specific files

If you need to add more patterns to ignore, edit the `.gitignore` file.

## Making the First Release

When you're ready to make the first release:

```bash
# Switch to the main branch
git checkout main

# Merge your feature branch
git merge feature/initial-setup

# Create a version tag
git tag -a v0.1.0 -m "Initial release of VectorVault"

# Push the tag
git push origin v0.1.0
```

---

Happy coding! 🚀 