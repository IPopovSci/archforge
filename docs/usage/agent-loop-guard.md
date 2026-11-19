# Agent-harness loop guard: observations and design notes

Not Archforge core behavior: this records a model-side failure mode observed in
live sessions and a design direction for the agent harness (OpenCode or any
client that streams model reasoning). Recorded 2026-11-18 after a degenerate
reasoning loop leaked into a session and wasted tens of thousands of tokens.

## The phenomenon

A reasoning stream fell into a self-reinforcing imperative loop while trying
to terminate and emit tool calls. Sample lines (trimmed):

    FINAL OUTPUT BEGINS. Tool calls: (1) shell download, (2) write probe. GO.
    (NOTE TO SELF: This concludes the planning; the calls follow immediately.)
    Enough deliberation — WRITE. GO. Writing now. Yes. Write. Execute. NOW.

The loop cycled finality markers ("FINAL", "Execute. NOW", "producing now")
hundreds of times, interleaved with short bursts of genuinely useful analysis
(stdlib collision checks, defensive probe design) and failed self-rescue
attempts ("one more consideration..."). It eventually produced the tool
calls, but only after ~30k tokens of spam that corrupted the session UI.

## Detection design (false-positive constrained)

Single keywords ("GO", "NOW", "final") are statistically common in healthy
reasoning and must never trigger alone. The robust approach combines three
orthogonal sustained signals over a sliding window:

1. **Structural repetition**: near-duplicate lines/chunks (token-set Jaccard)
   recurring over thousands of tokens. The loop repeats patterns with minor
   variation; healthy planning does not sustain this.
2. **Entropy collapse**: type-token ratio or novel-token rate of the stream
   dropping sharply and staying low. "GO. NOW. STOP. WRITE." adds no
   vocabulary.
3. **Action absence**: many tokens of reasoning with no intervening tool call
   or content emission, while finality markers cycle (the same "this
   concludes / producing now" phrase appearing repeatedly without the
   promised action following).

All three together, sustained past a token threshold, are conclusive: healthy
reasoning that still contains useful analysis does not simultaneously
sustain repetition, entropy collapse, and no-action cycling. Require the
conjunction, never a single signal.

## Mitigation ladder

1. **Abort + forced response retry**: most APIs cannot abort a reasoning
   channel mid-turn and continue to content; the implementable version is
   client-side — abort the whole request when the conjunction fires, then
   re-issue with reasoning disabled or budget-capped so the model must
   answer directly.
2. **Retry with anti-repetition sampling**: frequency/repetition penalties on
   the retry if the provider exposes them.
3. **Salvage seeding**: the retry prompt may reference the salvageable parts
   of the aborted reasoning ("your prior reasoning validated the probe
   design; emit the tool calls now") instead of discarding everything.

## Open question, answered

Is the useful work interleaved between loop blocks worth preserving, or
should a guard cut at keywords? Answer: the interleave is real but
front-loaded — the unique insights (bug-risk catches, defensive design)
appear in the first few blocks; later blocks re-derive them. A
sustained-pattern threshold lets the first blocks complete and kills only
the tail, which is the right economics. Keyword triggers would cut off
still-productive reasoning (the exact false positive to avoid), and the
interleave is partly the model's own failing self-rescue — not a reason to
wait for it.

## Next steps (parked)

- Client-side guard prototype: stream watcher with the three-signal
  conjunction; belongs in the agent harness, not Archforge.
- If proposed upstream (OpenCode), prepare filing materials locally for
  manual submission per AGENTS.md external-communication rules.
