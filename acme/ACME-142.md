# ACME-142 — Align `binomial_tree` with the core naming standard

**Requested by:** Pat (PM, Platform) · **Component:** acme-core / generators · **Priority:** normal

## Original request (Pat, as filed)

> Can we rename `binomial_tree` so it matches the other generators? New folks keep asking why it's the odd one out when everything else ends in `_graph`. The old name should keep working for a while so nothing breaks.

## Triage notes (tech lead)

Our naming standard says graph constructors end in `_graph`. `binomial_tree` predates the standard. Three internal usages exist, all in test code; one is at module level, which matters for the deprecation procedure.

## Ask

Introduce `binomial_tree_graph` as the canonical name. Keep `binomial_tree` working with a deprecation notice per the core deprecation procedure, and schedule its removal two minor versions out.

## Acceptance criteria (set at triage)

- New name documented in the API reference and tested.
- Old name warns and still returns identical graphs.
- Full test suite and convention guard green.
- PR carries the `type: API` label.
- No optional-dependency imports added at module level.

*(Synthesized ticket for the Acme scenario. Pat's request is the non-technical ask; the triage notes and acceptance criteria are what engineering adds before work starts.)*
