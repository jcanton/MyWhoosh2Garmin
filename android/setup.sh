#!/data/data/com.termux/files/usr/bin/bash
# One-time setup of MyWhoosh2Garmin in Termux, run from the repo checkout:
#   bash android/setup.sh
# Safe to re-run: it keeps an existing .env and virtual environment.
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
cd "$REPO"

echo "==> Installing Python, and Rust to build pydantic-core"
pkg install -y python rust

if [ ! -x .venv/bin/python ]; then
    echo "==> Creating the virtual environment"
    python -m venv .venv
fi

echo "==> Installing the pinned dependencies"
echo "    The first time, compiling pydantic-core takes 10-15 minutes."
.venv/bin/pip install --require-hashes -r android/requirements.txt

if [ ! -s .env ]; then
    echo "==> MyWhoosh credentials, stored in $REPO/.env"
    read -r -p "MyWhoosh email: " email
    read -r -s -p "MyWhoosh password: " password
    echo
    # Single-quoted values are taken literally by python-dotenv, once
    # backslashes and single quotes are escaped.
    password=${password//\\/\\\\}
    password=${password//\'/\\\'}
    (umask 077 && printf "MYWHOOSH_EMAIL=%s\nMYWHOOSH_PASSWORD='%s'\n" \
        "$email" "$password" > .env)
fi

echo "==> Adding the home-screen shortcut"
# ~/.shortcuts feeds the Termux:Widget list widget; dynamic_shortcuts feeds
# the app shortcuts shown when long-pressing the Termux:Widget app icon,
# which can be dragged out as a normal launcher icon.
for dir in ~/.shortcuts ~/.termux/widget/dynamic_shortcuts; do
    mkdir -p "$dir"
    printf '#!/data/data/com.termux/files/usr/bin/bash\nexec bash "%s/android/run.sh" "$@"\n' \
        "$REPO" > "$dir/MyWhoosh2Garmin"
    chmod 700 "$dir/MyWhoosh2Garmin"
done
# Termux:Widget uses ~/.shortcuts/icons/<script name>.png as the icon.
mkdir -p ~/.shortcuts/icons
cp android/icon.png ~/.shortcuts/icons/MyWhoosh2Garmin.png
chmod -R a-x,u=rwX,go-rwx ~/.shortcuts/icons

echo
echo "Setup done. Now running a first sync: Garmin Connect asks for your"
echo "login once, then the session is kept in $REPO/.garth."
echo
exec bash android/run.sh
