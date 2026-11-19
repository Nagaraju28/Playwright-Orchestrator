<!-- BEGIN PROJECT BRAIN — auto-generated, do not edit inside this block -->
This project's engineering memory is maintained by Project Brain.
Treat the rules below as BINDING on any change you make to this repository.
They are captured from this repo's own code, docs and history — where they
conflict with your assumptions, follow them or ask the user.

For the full, per-file detail (this file is a capped summary), run:
    brain context <path/to/file>     # everything known about one file
    brain export                     # the complete memory snapshot

## Instructions for AI Agents
# Follow these steps before modifying ANY file in this repository:
#
# 1. Call MCP tool: get_context(file="<path of file you are about to change>")
#    This returns constraints, failures, business rules, and decisions specific
#    to that file. Read them before writing a single line.
#
# 2. Do NOT violate any [HIGH] severity constraint without explicit
#    developer approval.
#
# 3. If you discover new constraints or decisions during your session,
#    call MCP tool: record_memory(...) to capture them immediately.
#
# 4. If working on a feature with an active spec in .brain/specs/, call get_spec(...)
#    or inspect requirements.md and design.md before generating code. Do NOT violate
#    design invariants.
#
# MCP server name: project-brain
# Available tools: get_context, get_file_context, get_business_rules,
#                  get_decisions, get_constraints, get_failures,
#                  record_memory, get_status, list_specs, get_spec
#
# 5. IF YOU CANNOT SEE THOSE TOOLS in this session, Brain's MCP server is not
#    reachable here. Tell the user in your first reply, in one line:
#
#      "Brain's MCP tools aren't available in this session. Run `brain doctor`
#       in this repo once, then restart the editor and approve project-brain."
#
#    Both halves are needed and in that order. A fresh clone has no MCP config at
#    all — those files carry absolute paths, so they are per-machine and never
#    committed — and any brain command writes them. The restart is then required
#    because an MCP server is only ever discovered at session start.
#
#    Then carry on using the rules below. They are the guaranteed floor: complete
#    enough to work from, just not per-file, and they need no MCP at all.


## Constraints — Technical boundaries that must not be violated

### server/src/api/projects.py

- [HIGH] Uploaded bundle must be a .zip file
  > Source: server/src/api/projects.py
  > Captured: 2026-11-19

### server/src/auth.py

- [HIGH] Missing required X-Agent-Token header
  > Source: server/src/auth.py
  > Captured: 2026-11-19
<!-- END PROJECT BRAIN -->
