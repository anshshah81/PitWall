# Environment Variables Setup

## Backend Environment (.env)

Create a file named `.env` in the `backend/` folder with these contents:

```env
# Anthropic Claude API Key
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OpenWeather API Key  
# Get from: https://openweathermap.org/api
OPENWEATHER_API_KEY=your-openweather-key-here
```

### How to Get Anthropic API Key

1. Go to https://console.anthropic.com/
2. Click "Sign Up" (or "Sign In" if you have an account)
3. Complete email verification
4. Navigate to "API Keys" in the dashboard
5. Click "Create Key"
6. Copy the key (starts with `sk-ant-`)
7. Paste it in your `.env` file

### How to Get OpenWeather API Key

1. Go to https://openweathermap.org/api
2. Click "Sign Up" (free account)
3. Complete email verification
4. Go to your account → API keys tab
5. Copy the default API key (or create a new one)
6. Paste it in your `.env` file

## Frontend Environment (.env.local)

Create a file named `.env.local` in the `frontend/` folder with these contents:

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Note:** This should point to wherever your backend is running. For local development, use `http://localhost:8000`.

## Verification

After creating both files, verify they're correct:

### Test Backend .env
```bash
cd backend
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Anthropic:', os.getenv('ANTHROPIC_API_KEY')[:10] if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET')"
```

Should output: `Anthropic: sk-ant-xxx`

### Test Frontend .env.local
```bash
cd frontend
node -e "require('dotenv').config({path:'.env.local'}); console.log('API URL:', process.env.NEXT_PUBLIC_API_URL)"
```

Should output: `API URL: http://localhost:8000`

## Security Notes

⚠️ **NEVER commit .env files to git!**

Both `.env` and `.env.local` are already in `.gitignore` to prevent accidental commits.

### What's Safe to Share
- ✅ Template files (ENV_TEMPLATE.md)
- ✅ Variable names
- ✅ Documentation

### What to NEVER Share
- ❌ Actual API keys
- ❌ `.env` file contents
- ❌ Screenshots showing API keys

## Troubleshooting

### "API key not found" error

**Symptom:** Backend logs show "ANTHROPIC_API_KEY not found"

**Fix:**
1. Check `.env` file exists in `backend/` folder
2. Check file is named exactly `.env` (not `.env.txt`)
3. Check no extra spaces around `=` sign
4. Restart backend server after creating/editing `.env`

### Frontend can't connect to backend

**Symptom:** Browser console shows CORS errors or connection refused

**Fix:**
1. Check backend is running (`http://localhost:8000/health` should work)
2. Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
3. Restart frontend dev server after editing `.env.local`

### Invalid API key error

**Symptom:** 401 Unauthorized from Anthropic API

**Fix:**
1. Verify API key is correct (check console.anthropic.com)
2. Check key hasn't been revoked
3. Check no extra characters or spaces in `.env`
4. Generate a new key if needed

## Example Working .env Files

### backend/.env (example)
```env
ANTHROPIC_API_KEY=sk-ant-api03-abc123xyz789...
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

### frontend/.env.local (example)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Quick Copy-Paste Templates

### For Windows PowerShell

```powershell
# Create backend .env
@"
ANTHROPIC_API_KEY=your-key-here
OPENWEATHER_API_KEY=your-key-here
"@ | Out-File -FilePath backend\.env -Encoding utf8

# Create frontend .env.local
@"
NEXT_PUBLIC_API_URL=http://localhost:8000
"@ | Out-File -FilePath frontend\.env.local -Encoding utf8
```

### For Mac/Linux Bash

```bash
# Create backend .env
cat > backend/.env << EOF
ANTHROPIC_API_KEY=your-key-here
OPENWEATHER_API_KEY=your-key-here
EOF

# Create frontend .env.local
cat > frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

Then edit the files to add your actual keys.

## Done!

Once you have both `.env` files created with valid API keys, you're ready to start the servers!

Next steps: See `QUICKSTART.md`
