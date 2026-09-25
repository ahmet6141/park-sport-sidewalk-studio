@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Publish-GitHub.ps1"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Islem tamamlanmadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b %RESULT%
