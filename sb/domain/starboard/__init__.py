"""STARBOARD subsystem (the `_unmapped` starboard-family re-home; NEW
subsystem birth) — the shipped `!starboard` config command group
(disbot/cogs/starboard_cog.py) + the BaseView config panel
(disbot/views/starboard/config_panel.py) at oracle byte parity.

Under-port boundary (sb/domain/starboard/service.py module docstring):
the reaction-listener pipeline (`on_raw_reaction_add/remove` →
handle_star_change → starboard_entries) is deliberately NOT ported —
no golden pins a reaction step; it lands with the reaction-surfaces
slice (sb/kernel/interaction/reactions.py names starboard as a
successor reaction surface).
"""
