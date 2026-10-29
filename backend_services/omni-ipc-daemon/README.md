# omni-ipc-daemon

The daemon lives in one place: **`Admin/omni_live_daemon_server.py`** (ports 9100/5000/5005/9101).
`omni_live_daemon_server.py` here is only a redirect that starts that file, kept so old scripts and
shortcuts still work. Don't add daemon code here (issue #6).

Other files in this folder (`omni_defensive_parser.py`, `omni_phase1_security_suite.py`,
`omni_flet_desktop_control_panel.py`) are standalone utilities and aren't part of the daemon.
