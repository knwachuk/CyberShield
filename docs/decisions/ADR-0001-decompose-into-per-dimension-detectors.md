# ADR-0001 — Decompose detection into per-dimension detectors

**Status:** Accepted

## Context

Abuse is not a single property of a message; it is a property of a relationship
in a context, made up of several distinct dimensions (directionality, content
severity, intent, persistence, power, and the harder corners of consent and
norms). A single end-to-end "is this abusive?" classifier collapses all of these
into one opaque number. That is brittle in three ways: it cannot say *why* it
fired, it cannot be improved one facet at a time, and it forces dimensions with
very different tractability — a follower-count ratio versus detecting sarcasm —
to share one model and one error budget.

## Decision

We build one detector per dimension rather than one model for the whole problem.
Each detector is a small, independently testable component that looks at exactly
one facet, declares which engine owns it, and produces a score plus evidence. The
catalog of detectors lives in this directory's README and is the development
backlog. A detector may itself wrap a model, a rule, or a graph query — the
contract is the same regardless of implementation.

## Consequences

We gain modularity: a new signal is a new detector behind the existing interface,
and a weak detector can be improved or swapped without disturbing the others. We
gain honesty about tractability, because each detector carries its own confidence
and the system can lean on the strong ones and route on the weak ones. We accept
added orchestration cost — there is now a fusion step (ADR-0004) to combine
detector outputs — and we accept that detectors must agree on a shared evidence
and score format (ADR-0002, ADR-0003).

## Alternatives considered

A single multi-task classifier was rejected because it sacrifices explainability
and per-facet iteration for marginal convenience. A pure rules engine was rejected
because the content dimensions genuinely need learned models. The decomposition
keeps rules and models side by side, each where it is strongest.
