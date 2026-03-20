@echo off
echo ============================================================
echo   MOVIE NOTIFIER SETUP
echo ============================================================
echo.

echo [1] Checking Python version...
python --version
if errorlevel 1 (
    echo   ❌ Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

echo.
echo [2] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo   ⚠️  Failed to install dependencies
    echo   You can try manually: pip install -r requirements.txt
)

echo.
echo [3] Creating directories...
if not exist config mkdir config
if not exist data mkdir data
if not exist logs mkdir logs
if not exist scripts mkdir scripts
echo   ✓ Directories created

echo.
echo [4] Checking configuration...
if exist config\config.yaml (
    echo   ✓ Configuration file already exists
) else (
    echo   ⚠️  Configuration file not found
    echo   Please copy config\config.yaml.example to config\config.yaml
    echo   and update it with your API keys and email settings.
)

echo.
echo [5] Checking scripts...
set missing=0
if not exist scripts	mdb_client.py set missing=1
if not exist scripts\config_manager.py set missing=1
if not exist scripts\email_notifier.py set missing=1
if not exist scripts\movie_notifier.py set missing=1

if %missing%==1 (
    echo   ❌ Some script files are missing
) else (
    echo   ✓ All required scripts found
)

echo.
echo ============================================================
echo   SETUP COMPLETE
echo ============================================================
echo.

echo NEXT STEPS:
echo.
echo 1. Get a TMDB API Key:
echo    - Visit: https://www.themoviedb.org/settings/api
echo    - Create an account if needed
echo    - Request an API key
echo.
echo 2. Configure Email Settings:
echo    - For Gmail, create an App Password:
echo      https://myaccount.google.com/apppasswords
echo    - Use this password in the config file
echo.
echo 3. Edit Configuration File:
echo    - Open: config\config.yaml
echo    - Update TMDB API key
echo    - Update email settings
echo    - Add/remove actors/directors as needed
echo.
echo 4. Test the Setup:
echo    - Run: python scripts\movie_notifier.py --test
echo.
echo 5. Run Once to Test:
echo    - Run: python scripts\movie_notifier.py --once
echo.
echo 6. Set Up Scheduled Runs:
echo    - Use the cron job feature in AionUI
echo    - Or run: python scripts\movie_notifier.py --schedule
echo.
pause