#!/data/data/com.termux/files/usr/bin/bash
# Sync recent MyWhoosh rides to Garmin Connect and keep the log on screen.
# Started from the MyWhoosh2Garmin home-screen shortcut; see android/setup.sh.

REPO="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
cd "$REPO" || exit 1

.venv/bin/python myWhoosh2Garmin.py "$@"
status=$?

echo
if [ "$status" -eq 0 ]; then
    echo "Done."
else
    echo "Failed with exit code $status. Full log: $REPO/myWhoosh2Garmin.log"
fi
read -r -n 1 -s -p "Press any key to close."
echo
exit "$status"
