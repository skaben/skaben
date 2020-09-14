webview wrapper for any kind of interface

recommended distro: Xubuntu 18 LTS

with Cairo:

`
  apt-get update && \
  apt-get install -y --no-install-recommends \
  python-gi python-gi-cairo python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0 \
  build-essential libcairo2 libcairo2-dev libgirepository1.0-dev zlib1g-dev zlib1g bzip2
`

with QT:

app.py replace `webview.gui = "gtk"` with `webview.gui="qt"` - you're on your own :)
