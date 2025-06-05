@echo off
echo ========================================
echo Bug-Ridden Todo App Setup
echo ========================================
echo.

echo Installing Python dependencies...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install dependencies
    echo Make sure you have Python and pip installed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit config.json with your GitHub repository and token
echo 2. Run: python github_issue_importer.py --config config.json --dry-run
echo 3. If dry run looks good, remove --dry-run flag to create actual issues
echo 4. Open index.html in a browser to see the buggy app
echo.
echo For help: python github_issue_importer.py --help
echo.
pause
