#!/bin/bash
# Double-click this file in Finder to build the print sheet and open it.
cd "$(dirname "$0")" || exit 1
python3 make_print_sheet.py
open print_sheet.html
