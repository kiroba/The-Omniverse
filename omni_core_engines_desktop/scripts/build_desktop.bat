@echo off
echo  Building Omniverse Core Engines Desktop App for Windows...
cd desktop
call flutter pub get
call flutter build windows --release
echo  Windows Desktop Build Complete!
