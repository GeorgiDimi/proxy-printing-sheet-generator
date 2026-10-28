#!/bin/bash
# Double-click this file in Finder to build the print sheet and open it.
cd "$(dirname "$0")" || exit 1
python3 make_print_sheet.py || exit 1
# Open in Chrome if available (Safari mis-renders the print layout);
# otherwise fall back to the default browser.
if [ -d "/Applications/Google Chrome.app" ]; then
  open -a "Google Chrome" print_sheet.html || exit 1
else
  echo "Google Chrome not found — opening in the default browser."
  echo "Note: Safari has issues rendering the print layout; Chrome is recommended."
  open print_sheet.html || exit 1
fi

# Everything succeeded — close this Terminal window.
# (If any step above failed, the script already exited and the window stays
# open so you can read the error.)
osascript -e 'tell application "Terminal" to close (every window whose name contains "Make Print Sheet.command")' >/dev/null 2>&1 &
exit 0
