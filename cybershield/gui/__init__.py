"""Local web GUI for CyberShield.

The GUI primarily drives the Cyber Shield engine: enter two accounts on a
platform, run the comparison, and read the abuse report. It also surfaces the
Identity Reconciliation engine as a secondary tool.

Run it with ``python run_gui.py`` from the project root.
"""

from cybershield.gui.app import create_app

__all__ = ["create_app"]
