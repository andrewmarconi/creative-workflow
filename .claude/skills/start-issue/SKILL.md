---
name: start-issue
description: Read a GitHub issue, create an appropriate feature or bugfix branch, and set up working context
---

# Start Issue Skill

Automates the workflow of starting work on a GitHub issue by reading the issue details, creating an appropriate branch, and providing working context.

## Usage

```bash
/start-issue <issue-number>
```

## Skill Execution Instructions

When invoked with an issue number, execute the following steps:

### 1. Get Current Repository Context

First, identify the current repository from git remote:

```bash
git remote -v | grep origin | head -n 1
```

Parse the owner and repo from the output (e.g., `https://github.com/owner/repo.git` or `git@github.com:owner/repo.git`).

### 2. Read the GitHub Issue

Use the GitHub MCP tool to read the full issue details:
- Issue title
- Issue body/description
- Labels
- Assignees
- Milestone
- Current state

### 3. Determine Branch Type

Analyze the issue labels to determine branch type:
- If labels include `bug`, `bugfix`, `fix`, or similar → create `bugfix/` branch
- If labels include `feature`, `enhancement`, `improvement`, or similar → create `feature/` branch
- If unclear from labels, ask the user which type to use

### 4. Create Branch Name

Generate a branch name from the issue:
- Format: `{type}/{issue-number}-{slug}`
- Where `{slug}` is a kebab-case version of the issue title (lowercase, spaces to dashes, max 50 chars)
- Example: `feature/42-add-user-authentication` or `bugfix/123-fix-login-error`

### 5. Create and Checkout Branch

Create the new branch from the current main/master/develop branch (check which is the default):

```bash
git checkout -b {branch-name}
```

### 6. Display Issue Context

Present a clear summary of the issue to work on:
```
# Issue #{number}: {title}

**Type**: {feature/bugfix}
**Branch**: {branch-name}
**Labels**: {labels}
**Assignee**: {assignee or "Unassigned"}

## Description
{issue body}

## Checklist
- [ ] Read and understand the issue
- [ ] Implement the changes
- [ ] Write/update tests
- [ ] Update documentation if needed (verify docs/ builds)
- [ ] Run documentation build verification
- [ ] Create pull request

---
Ready to start working on this issue!
```

### 7. Success Message

Confirm that:
- Issue has been read and understood
- Branch has been created and checked out
- Context is ready for development

### 8. Verify Documentation

After setting up the branch, check if documentation updates are needed:

```bash
# Check current documentation state
ls -la docs/

# Verify documentation builds successfully
cd docs && make clean && make html
```

If the issue involves:
- New features → Remind to update relevant `.rst` files in `docs/`
- API changes → Remind to update API documentation
- Configuration changes → Remind to update `docs/configuration/`
- New models/commands → Remind to document in appropriate sections

Display a reminder:
```
📚 Documentation Check:
- [ ] Review if docs/ needs updates for this issue
- [ ] Run: cd docs && make html (to verify docs build)
- [ ] Check: docs/_build/html/index.html (to preview changes)

Relevant documentation areas:
- User guide: docs/user/
- Developer guide: docs/developer/
- API reference: docs/api/
```

## Notes

- If the repository owner/name cannot be determined from git remote, ask the user
- If git is not in a clean state (uncommitted changes), warn the user before creating the branch
- Store the issue number in a git note or branch description if the git hosting service supports it
- If the issue is already closed, warn the user but proceed anyway

## Examples

### Example 1: Feature Issue
```
$ /start-issue 42

Reading issue #42 from github/repo...

# Issue #42: Add user authentication system

**Type**: Feature
**Branch**: feature/42-add-user-authentication
**Labels**: enhancement, user-experience
**Assignee**: @username

## Description
We need to implement a user authentication system with the following features:
- Login/logout functionality
- Password reset
- OAuth integration

Created branch: feature/42-add-user-authentication
Ready to start working!
```

### Example 2: Bugfix Issue
```
$ /start-issue 123

Reading issue #123 from github/repo...

# Issue #123: Login button throws 500 error

**Type**: Bugfix
**Branch**: bugfix/123-login-button-throws-500-error
**Labels**: bug, critical, backend
**Assignee**: Unassigned

## Description
When clicking the login button on the home page, the application returns a 500 error...

Created branch: bugfix/123-login-button-throws-500-error
Ready to start working!
```

## Error Handling

- **Not a git repository**: Display error and exit
- **No remote named 'origin'**: Ask user for owner/repo
- **Issue not found**: Display error and suggest checking the issue number
- **Branch already exists**: Ask user if they want to switch to it or create a new name
- **Network error**: Display error and suggest checking internet connection

---

## Implementation Tips

When implementing this workflow:

1. **Use GitHub MCP tools** for reading issue data
2. **Parse git remote** carefully to handle both HTTPS and SSH URLs
3. **Sanitize branch names** to remove special characters
4. **Check git status** before creating branches to avoid losing work
5. **Provide clear feedback** at each step so the user knows what's happening
6. **Verify documentation** builds successfully with `cd docs && make html`
7. **Suggest relevant documentation areas** based on issue type and labels
