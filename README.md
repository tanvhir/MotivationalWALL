# Motivation Wallpaper

A tiny Windows app that automatically downloads motivational wallpapers and changes your desktop background.

## Easiest way: GitHub Actions

You do NOT need Python installed on your PC.

1. Create a new GitHub repository.
2. Upload all files from this folder.
3. Open the **Actions** tab.
4. Choose **Build Windows EXE**.
5. Click **Run workflow**.
6. Wait for the build to finish.
7. Open the completed workflow run.
8. Download the artifact named `MotivationWallpaper-Windows`.
9. Extract it and double-click `MotivationWallpaper.exe`.

## Notes

The app searches Bing Images for the phrase you enter. Image ownership/licensing belongs to the respective image owners. Use searches that return wallpapers you are permitted to use.

The app stores downloaded images in:
`%APPDATA%\MotivationWallpaper\wallpapers`

Settings are stored in:
`%APPDATA%\MotivationWallpaper\config.json`
