webview wrapper for any kind of interface

recommended distro: Xubuntu 18 LTS

with Cairo:

`apt-get install -y --no-install-recommends python3 python3-dev python3-venv python3-cairo python3-cairo-dev python3-gi python3-gi-cairo gir1.2-gtk-3.0 build-essential libcairo2 libcairo2-dev libgirepository1.0-dev zlib1g-dev zlib1g libbz2 libbz2-dev`

with QT:

app.py replace `webview.gui = "gtk"` with `webview.gui="qt"` - you're on your own :)
