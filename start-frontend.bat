@echo off
echo ========================================
echo PitWall Frontend - Starting...
echo ========================================
echo.

cd frontend

if not exist node_modules (
    echo Installing dependencies...
    call npm install
)

echo.
echo Starting Next.js dev server...
echo App will be available at: http://localhost:3000
echo.

call npm run dev
