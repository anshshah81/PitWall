@echo off
echo ========================================
echo PitWall Data Preparation
echo ========================================
echo.
echo This will download F1 data from FastF1
echo This may take 15-20 minutes
echo.
pause

cd data_prep

if not exist ..\backend\venv (
    echo ERROR: Backend virtual environment not found
    echo Please run start-backend.bat first
    pause
    exit /b 1
)

call ..\backend\venv\Scripts\activate

echo.
echo Downloading F1 race data...
echo.

python fetch_reference_data.py

echo.
echo ========================================
echo Data preparation complete!
echo Cache location: backend\data\cache\
echo ========================================
pause
