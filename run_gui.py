#!/usr/bin/env python3
"""Launch the CyberShield web GUI.

Usage:
    python run_gui.py                 # serves on http://127.0.0.1:5000
    CYBERSHIELD_ANALYZER_MODE=full python run_gui.py   # use transformer models

The GUI primarily drives the Cyber Shield abuse-comparison engine. With no
Twitter credentials configured it runs against the bundled sample accounts, so
it works fully offline for demos and development.
"""

from cybershield.gui import create_app


def main() -> None:
    app = create_app()
    # debug=False keeps the reloader from importing engines twice; flip to True
    # during template development.
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
