"""
aede.trace — GEPA (Generative Execution Path Audit) trace subsystem.

Provides append-only JSONL trace logging for agent turns.
"""
from aede.trace.logger import TraceLogger

__all__ = ["TraceLogger"]
