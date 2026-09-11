# Attention Guard v3: Native SDK Compaction Integration

## Architecture Decision
Instead of relying on a fragile Python script checking `transcript.jsonl` byte size (`auto-compact.py`), we will migrate the context auto-compaction logic to use the official Google Antigravity SDK API: `@hooks.on_compaction`.

## Proposed Changes
1. **[DELETE]** `scripts/auto-compact.py` and the `PreInvocation` hook from `hooks.json`.
2. **[NEW]** `plugin.py` (Antigravity SDK format):
   - Initialize the plugin using the native Python SDK.
   - Decorate a handler with `@hooks.on_compaction`.
   - When triggered, execute the "Sliding Window Semantic Anchoring" algorithm to synthesize Tier 1 summaries and truncate older Tier 2 execution logs.
3. **[MODIFY]** `compaction.json`: Update schema to support the native SDK format.

## Verification
- Run the plugin locally in SDK mode and force a 135k token breach to trigger the `@hooks.on_compaction` event.
