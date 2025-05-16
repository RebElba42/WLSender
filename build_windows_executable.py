# build_windows_executable.py
# dont forget "pip install pyinstaller first"
# This script builds a Windows executable for the WLSender application using PyInstaller.
# It includes the necessary data files and sets the application icon.
import PyInstaller.__main__

PyInstaller.__main__.run([
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--add-data=icons;icons',
    '--add-data=i18n;i18n',
    '--icon=icons/wlgate.png',
     '--name=WL-QSO-Sender',
    'src/main.py',
])
print("\Ready!")