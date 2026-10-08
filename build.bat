@echo off
python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --windowed --name MotivationWallpaper motivation_wallpaper.py
echo.
echo Build complete. Your EXE is in the dist folder.
pause
