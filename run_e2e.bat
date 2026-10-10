@echo off
REM Script Windows pour lancer les tests E2E

echo ============================================================
echo   GROUPPAY E2E TESTS (Windows)
echo ============================================================
echo.

REM Verifier serveur
curl -s http://127.0.0.1:8000/health/ > nul 2>&1
if errorlevel 1 (
    echo XX Le serveur Django n'est pas lance sur http://127.0.0.1:8000
    echo    Lance dans un autre terminal : python manage.py runserver
    exit /b 1
)

echo OK Serveur Django accessible
echo.

REM Mode
set MODE=%1
if "%MODE%"=="" set MODE=all

if "%MODE%"=="all" (
    echo ^>^>^> Tous les tests E2E
    pytest tests/e2e/ -m e2e --tb=short
) else if "%MODE%"=="headed" (
    echo ^>^>^> Tests E2E avec navigateur visible
    pytest tests/e2e/ -m e2e --headed --tb=short
) else if "%MODE%"=="smoke" (
    echo ^>^>^> Tests smoke
    pytest tests/e2e/test_auth.py tests/e2e/test_navigation.py -m e2e --tb=short
) else (
    echo Usage: run_e2e.bat [all^|headed^|smoke]
)

echo.
echo ============================================================
echo   FIN DES TESTS
echo ============================================================
