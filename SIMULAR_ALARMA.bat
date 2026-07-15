@echo off
REM Doble clic en este archivo = suena la alarma de prueba en tu celular.
REM Usa simular_wally.py. Para eliminar la prueba, borra ambos archivos.
cd /d "%~dp0"
venv\Scripts\python.exe simular_wally.py
echo.
pause
