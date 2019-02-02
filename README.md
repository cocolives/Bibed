
# Quick start (on Arch Linux)


## First run

```
# change to your projets/sources directory
yaourt python-bibtexparser-git
yaourt python-sentry_sdk
pacman -S git gobject-introspection python-inotify
git clone https://github.com/cocolives/Bibed.git
cd Bibed
sudo ln -sf `pwd`/Bibed /usr/bin/
ln -sf es.cocoliv.bibed.desktop ~/.local/share/applications/
```

Then, launch the application from anywhere. The executable name is `Bibed`.


# Developer installation

## System

Please make sure the following packages are installed:

```
gobject-introspection
```

## Python 3

In a virtual environment:

```
pip install -r requirements.txt
```

Note: `Bibed` is developed under `Arch Linux` with `Python` 3.7.2.


## Optional packages

```
ipython
git-up
```
