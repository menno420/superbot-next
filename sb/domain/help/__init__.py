"""Band 1 — the HELP subsystem: help-as-projection (design-spec K8 row;
help is a PROJECTION from the manifests, never a hand-list). service.py
derives the command inventory from sb.manifest and feeds the S9b
help_panel_spec; the `help.answer` legacy AI task is claimed here.

The shipped per-guild help OVERLAY lanes (services/help_overlay*.py —
operator copy overrides + their mutation pipeline) are a successor slice:
they need their own store + K7 ops (documented in D-0026)."""
