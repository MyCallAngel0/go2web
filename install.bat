@echo off
REM Check if running as administrator.
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This installation requires administrative privileges.
    echo Please right-click install.bat and select "Run as administrator".
    pause
    exit /b
)

echo Installing go2web CLI command...
REM Copy go2web.cmd and go2web.py to System32.
copy /Y "%~dp0go2web.cmd" "%WINDIR%\System32\go2web.cmd"
if %errorLevel% neq 0 (
    echo Failed to copy go2web.cmd. Check your permissions.
    pause
    exit /b
)
copy /Y "%~dp0go2web.py" "%WINDIR%\System32\go2web.py"
if %errorLevel% neq 0 (
    echo Failed to copy go2web.py. Check your permissions.
    pause
    exit /b
)

echo Installation complete!
echo You can now run "go2web" from any Command Prompt.
pause
