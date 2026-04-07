# Aegis Vault Index

## Overview

This vault stores local outputs from the early-stage Aegis Security Research System.

Current v1 focus:

- deterministic HTTP testing
- IDOR-style identifier mutation
- local markdown evidence and memory

## Folders

- `endpoints/`: endpoint notes and request targets
- `resources/`: inferred resource notes
- `hypotheses/`: generated IDOR hypotheses
- `experiments/`: executed mutation records
- `findings/`: classified outcomes
- `raw/`: local JSON memory and state
- `notes/`: project notes and prompt references

## Usage

Run:

```bash
python scripts/run_agent.py
```

Then inspect the generated notes in the vault folders above.

## Status

The repository contains a first implementation pass, but it is still an early v1 and should not be treated as a complete autonomous pentesting system.
