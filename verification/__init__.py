"""verification/ — layer-V V-5: the `verified_live` sign-off registry
(verification-review §3.3 schema; TIERED per amendment A-18; verification
requirement per owner ruling Q-0244).

A live sign-off is never just a checkbox: every record carries the surface
under test, scenario, expected visible result + DB/audit/event effects,
signer, build SHA, evidence, and cutover status
(verification/verified_live.py — the schema; verification/verified_live.yml
— the registry data; tools/check_verified_live.py — the gate).

The two tiers (A-18, one schema field):
  automated       — the prefix-command lane (live agent testing) + the
                    slash/component lane per Q-0244: a slash/component
                    surface counts VERIFIED when its prefix twin passes
                    live agent testing AND the slash path passes the
                    in-process pipeline-true replay. No human click-through
                    required for sign-off.
  human_required  — the optional Q-0234 judgment walks ("works · logical ·
                    self-explanatory") + the A-10 automation-unreachable
                    surfaces. NOTHING in this lane blocks CUT-3: unsigned
                    human-tier rows are published as the named
                    coverage-debt list in the CUT-2/CUT-3 reaction window,
                    never silently dropped (the debt-list model).

Every subsystem starts UNVERIFIED; sign-offs happen at the port bands and
CUT milestones. Layer V sits outside the boot chain: nothing under sb/
imports verification/.
"""
