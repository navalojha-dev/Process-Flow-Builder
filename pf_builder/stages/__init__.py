"""Multi-stage agent pipeline.

Each stage is a small, focused LLM call with a structured JSON output.
Stages are composed by the orchestrator. Each stage exposes a single
`run(...) -> dict` function so they're easy to test independently.
"""
