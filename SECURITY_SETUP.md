# Security Setup Guide

## ⚠️ IMPORTANT: Protecting Sensitive Data

This repository has been configured to prevent accidental exposure of sensitive credentials to public repositories.

## Quick Setup

### 1. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder values with your actual credentials:

```
FS_USER_ID=your_actual_user_id
FS_PASSWORD=your_actual_password
FS_TOTP=your_actual_totp
FS_VENDOR_CODE=your_actual_vendor_code
FS_API_KEY=your_actual_api_key
```

### 2. Configure User Settings

Copy the example user configuration file:

```bash
cp client/user_config.json.example client/user_config.json
```

Edit `client/user_config.json` and replace the placeholder values with your actual user information.

### 3. Install Dependencies

Make sure to install the required Python packages including the new `python-dotenv` dependency:

```bash
pip install -r requirements.txt
```

## Files Protected by .gitignore

The following files contain sensitive data and are **excluded from git**:

- `.env` - Environment variables with API credentials
- `client/user_config.json` - User configuration with passwords
- `*.env` - Any other environment files

## Safe Files to Commit

These template files are safe to commit to the repository:

- `.env.example` - Template for environment variables
- `client/user_config.json.example` - Template for user configuration
- `client/broker_config.json` - Broker API endpoints (no credentials)

## Before Pushing to Public Repository

1. ✅ Verify `.gitignore` includes sensitive files
2. ✅ Check that `.env` and `user_config.json` are NOT tracked by git
3. ✅ Only commit `.example` template files
4. ✅ Run: `git status` to confirm no sensitive files are staged

## Verify Your Configuration

To verify that your sensitive files are properly ignored:

```bash
git status --ignored
```

You should see `.env` and `client/user_config.json` in the ignored files list.

## Running Tests

After setting up your `.env` file, you can run the test file:

```bash
python client/test_FSClientWrapper.py
```

The test will now load credentials from your `.env` file automatically.

## Security Best Practices

1. **Never commit real credentials** to version control
2. **Always use environment variables** for sensitive data
3. **Keep `.env` file local** and never share it
4. **Rotate credentials** if they are accidentally exposed
5. **Review changes** before pushing to ensure no sensitive data is included

---

**Note**: If you accidentally committed sensitive data, remove it from git history immediately using tools like `git filter-branch` or `BFG Repo-Cleaner`, and rotate all exposed credentials.
