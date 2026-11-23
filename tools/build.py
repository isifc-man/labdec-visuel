#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Point d'entrée unique :  /usr/bin/python3 tools/build.py"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render
import pages_pred
import build_interactive

if __name__ == "__main__":
    render.SCHEMA_HOOK = pages_pred.schema_for_montage
    code = render.main()
    pages_pred.main()
    build_interactive.generate()
    sys.exit(code)
