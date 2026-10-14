"""Text parsers shared by every state adapter (no I/O, no dependencies beyond the standard library)."""

from lotline.parse.permit_text import PermitTextFacts, parse_description

__all__ = ["PermitTextFacts", "parse_description"]
