@echo off

python -m nuitka ^
  --onefile ^
 --enable-plugin=pyqt6 ^
 --include-qt-plugins=platforms,styles,imageformats,iconengines ^
 --include-data-files=*.ui=ui/ ^
 --windows-disable-console ^
 --assume-yes-for-downloads ^
 installer.py

pause