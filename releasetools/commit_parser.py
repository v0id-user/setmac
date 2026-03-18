"""Custom commit parser that supports both conventional and legacy commit(type): format."""

from re import sub

from semantic_release.commit_parser.conventional.parser import (
    ConventionalCommitParser,
    ConventionalCommitParserOptions,
)
from semantic_release.commit_parser.token import ParsedMessageResult


def _normalize_message(message: str) -> str:
    """Convert commit(type): msg to type: msg for backward compatibility."""
    return sub(r"^commit\((feat|fix|chore|docs|style|refactor|test|ci|perf|build)\):\s*", r"\1: ", message, count=1)


class SetmacCommitParser(ConventionalCommitParser):
    """Parser that accepts both conventional and legacy commit(type): format."""

    def parse_message(self, message: str) -> ParsedMessageResult | None:
        normalized = _normalize_message(message)
        return super().parse_message(normalized)
