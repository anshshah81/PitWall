@echo off
echo ========================================
echo PitWall Backend - Starting...
echo ========================================
echo.

cd backend

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

if not exist venv\Lib\site-packages\fastapi (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting FastAPI server on port 8000...
echo API docs will be available at: http://localhost:8000/docs
echo.

uvicorn main:app --reload --port 8000
