"""LexiMorph: name-derived vocabulary transpiled to Python."""

from leximorph.mapping import build_mapping, export_mapping
from leximorph.transpiler import transpile

__all__ = ["build_mapping", "export_mapping", "transpile"]
