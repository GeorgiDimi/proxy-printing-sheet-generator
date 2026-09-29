#!/bin/bash
# Double-click this file in Finder to build the print sheet and open it.
cd "$(dirname "$0")" || exit 1
python3 make_print_sheet.py
# Open in Chrome if available (Safari mis-renders the print layout);
# otherwise fall back to the default browser.
if [ -d "/Applications/Google Chrome.app" ]; then
  open -a "Google Chrome" print_sheet.html
else
  echo "Google Chrome not found — opening in the default browser."
  echo "Note: Safari has issues rendering the print layout; Chrome is recommended."
  open print_sheet.html
fi
