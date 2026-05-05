# Process Flow Builder

Claude Code skill that generates a tailored Shipsy process-flow PPTX from
a client meeting transcript.

## What it does

Reads a transcript → infers the client's business model, mile stages,
load type, geography, and industry vertical → produces a 3-slide PPTX:

1. **Process Flow with Shipsy** — Skynet-template grid (icons preserved),
   step labels tailored to the client's vocabulary.
2. **Our Learnings & Key Problems Identified** — client snapshot + pain
   points pulled from the transcript.
3. **Impact & Summary** — capabilities deployed | the AI impact.

## Usage (inside Claude Code)

Drop a transcript file somewhere accessible, then ask Claude:

```
/process-flow ~/Downloads/client-call.txt
```

or

```
generate a process flow for this client: ~/Downloads/client-call.txt
```

Claude will read the transcript, build the flow JSON, run the renderer,
visually verify the output, and place the PPTX at:

```
outputs/<client_short>_process_flow.pptx
```

## Manual usage (without Claude Code)

```bash
cd .claude/skills/process-flow
python3 -m pip install --user -r requirements.txt
# Author a flow JSON matching schema.json — see samples/tpn_flow.json
python3 render.py samples/tpn_flow.json /tmp/output.pptx
```

## Files

```
.
├── README.md                      this file
├── outputs/                       generated PPTX deliverables land here
└── .claude/skills/process-flow/
    ├── SKILL.md                   instructions Claude follows when invoked
    ├── render.py                  flow JSON + template → PPTX renderer
    ├── schema.json                JSON schema for the flow definition
    ├── requirements.txt           python deps (python-pptx, python-docx)
    ├── templates/
    │   └── process_flow.pptx      Skynet-derived single-slide template
    └── samples/
        ├── tpn_flow.json          worked example for The Pallet Network
        └── tpn_output.pptx        reference 3-slide deck
```

## Sample output

`samples/tpn_output.pptx` shows the generator running against The Pallet
Network (UK pallet hub-and-spoke network, Swadlincote hub, ~120 member
depots).

## Limitations

- The Skynet logo on slide 1 (top-right) is preserved from the template
  — for an external pitch you'll want to swap it manually.
- The 7-row layout is fixed (icons line up). Step labels are fully
  tailored, but the row skeleton matches Skynet's deck.
- English only.
