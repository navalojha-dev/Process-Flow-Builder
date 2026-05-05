"""Static analysis of the Shipsy codebase.

The scanner walks the Node.js / LoopBack codebase, extracts what
capabilities actually exist (modules, services, agents, integrations,
domain models, API endpoints), and produces a `codebase-features.json`
manifest. Stage 5 (validate) consults this manifest to flag to-be
bullets that cite capabilities the codebase doesn't back up.

This is Source 2 of the 5-source KB architecture
(see notes/capability-kb-architecture.md).
"""
