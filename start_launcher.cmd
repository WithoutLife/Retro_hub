@echo off
REM --- Устанавливаем текущую директорию как корень проекта ---
cd /d "%~dp0"

REM --- Настройка кодировки на UTF-8 (для кириллицы) ---
chcp 65001 >nul

REM --- Подавление предупреждений libpng/iCCP для Qt ---
SET QT_LOGGING_RULES=qt.image.png.warning=false

REM --- Запуск скрипта Python ---
"C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe" main_app.py

REM --- Сброс переменной среды (необязательно) ---
SET QT_LOGGING_RULES=

REM --- Ожидание, чтобы увидеть ошибку ---
echo.
echo ---------------------------------------
echo.
pause