# Deploy Frontend to Vercel

## 1. Import project

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New…** → **Project**.
3. Import the **PitWall** repo (`anshshah81/PitWall`).

## 2. Configure build

- **Framework Preset:** Next.js (auto-detected).
- **Root Directory:** Click **Edit** and set to **`frontend`** (important).
- **Build Command:** leave default (`npm run build` or `next build`).
- **Output Directory:** leave default.
- **Install Command:** leave default (`npm install`).

## 3. Environment variable

Add one variable:

| Name                     | Value                          |
|--------------------------|--------------------------------|
| `NEXT_PUBLIC_API_URL`    | Your Railway backend URL       |

Example: `https://your-app-name.up.railway.app`  
(No trailing slash. Copy from Railway → your service → Settings → Networking → Domain.)

## 4. Deploy

Click **Deploy**. Vercel will build and host the frontend. Your app URL will be like `https://pitwall-xxx.vercel.app`.

## 5. Backend CORS

The backend is already configured to allow requests from `*.vercel.app`. After you deploy, redeploy the Railway backend once so the CORS change is live (or it may already be deployed if you pushed the CORS update).

## Troubleshooting

- **"Failed to fetch" / CORS errors:** Ensure `NEXT_PUBLIC_API_URL` is the exact Railway URL and that the backend has been redeployed with the latest CORS settings.
- **Build fails:** Confirm Root Directory is `frontend`.
- **API 404:** Check that the Railway URL has no trailing slash and that the backend is running (open the URL in a browser; you should see `{"name":"PitWall API",...}`).
