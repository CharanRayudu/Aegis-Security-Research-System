# Prompt Notes

This file documents the intended reasoning style for the current v1.

## Core Prompt Intent

The v1 reasoner should stay narrow:

- focus only on IDOR and broken object-level authorization
- use endpoint shape and local memory as context
- generate a small number of deterministic hypotheses
- avoid broad or speculative attack classes

## Hypothesis Quality Rules

- prefer concrete identifier-based tests over generic fuzzing
- explain why the endpoint likely maps to a resource
- describe practical baseline-versus-mutated comparisons
- keep confidence grounded in evidence and context

## Validation Rules

- treat transport failures as inconclusive
- require real response differences before confirming a finding
- prefer conservative outputs over noisy false positives

## Future Prompt Work

- better resource inference from endpoint naming
- stronger use of historical memory
- more compact markdown summaries for generated notes
