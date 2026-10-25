#!/usr/bin/env bash
echo " Building Omniverse Core Engines Desktop App..."
cd desktop

flutter pub get

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo " Building Linux Desktop App..."
    flutter build linux --release
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo " Building macOS Desktop App..."
    flutter build macos --release
fi

echo " Desktop Build Complete!"
