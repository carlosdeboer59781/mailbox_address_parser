from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mailbox:
    """A single RFC 5322 mailbox address.

    Attributes:
        display_name: Optional human-readable name. May be None, a plain
            string, or a string derived from a quoted local-part. When parsed
            from a quoted-string display name, surrounding quote marks are
            removed and backslash escapes are unquoted (e.g. ``\"`` -> ``"``).
            Surrounding comments and folding whitespace are stripped before
            the mailbox is returned.
        local_part: The local part of the address (left of '@'). Quoted
            local-parts are returned unquoted and unescaped.
        domain: The domain part of the address (right of '@'). Returned as
            written, minus any inline comments.
    """

    display_name: str | None
    local_part: str
    domain: str


class _ParseError(ValueError):
    """Raised on unrecoverable mailbox syntax violations."""


def _skip_cfws(text: str, pos: int) -> int:
    """Advance ``pos`` past any CFWS — comments and folding whitespace.

    RFC 5322 allows arbitrary comments and linear whitespace (including
    CRLF sequences folded into the middle of a header field) between
    syntactic tokens. We collapse all of that here so the caller sees only
    the next meaningful character.
    """
    while pos < len(text):
        ch = text[pos]
        if ch.isspace():
            pos += 1
            continue
        if ch == "(":
            depth = 1
            pos += 1
            while pos < len(text) and depth:
                c = text[pos]
                if c == "\\":
                    pos += 2
                    continue
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                pos += 1
            if depth:
                raise _ParseError("unterminated comment")
            continue
        break
    return pos


def _parse_quoted(text: str, pos: int) -> tuple[str, int]:
    """Parse a quoted string starting at ``text[pos] == '"'``.

    Returns the unescaped contents and the index immediately past the
    closing quote. Implements the RFC 5322 quoted-pair rule: any character
    preceded by a backslash is taken literally, including quote marks and
    the backslash itself.
    """
    assert text[pos] == '"'
    pos += 1
    out: list[str] = []
    while pos < len(text):
        ch = text[pos]
        if ch == "\\":
            if pos + 1 >= len(text):
                raise _ParseError("trailing backslash in quoted string")
            out.append(text[pos + 1])
            pos += 2
            continue
        if ch == '"':
            return "".join(out), pos + 1
        out.append(ch)
        pos += 1
    raise _ParseError("unterminated quoted string")


def _parse_dot_atom(text: str, pos: int) -> tuple[str, int]:
    """Parse a dot-atom-text run (atext and dots, no surrounding CFWS).

    ``atext`` is defined in RFC 5322 section 3.2.3. We deliberately include
    only the production's printable subset — no control characters, no
    spaces, no specials — so callers receive a value already stripped of
    inline comments.
    """
    start = pos
    while pos < len(text):
        ch = text[pos]
        if ch in _ATEXT_CHARS or ch == ".":
            pos += 1
        else:
            break
    if pos == start or text[start] == "." or text[pos - 1] == ".":
        raise _ParseError("malformed dot-atom")
    return text[start:pos], pos


# atext per RFC 5322 §3.2.3, precomputed as a frozenset for fast membership.
_ATEXT_CHARS = frozenset(
    "!#$%&'*+-/=?^_`{|}~"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
)


def _parse_word(text: str, pos: int) -> tuple[str, int]:
    """Parse a single ``word`` token: either a quoted string or an atom.

    RFC 5322 treats an unquoted atom and a quoted string as interchangeable
    for building display names and local-parts. Folding that choice here lets
    the higher-level callers stay uniform.
    """
    pos = _skip_cfws(text, pos)
    if pos >= len(text):
        raise _ParseError("unexpected end of input")
    if text[pos] == '"':
        return _parse_quoted(text, pos)
    return _parse_dot_atom(text, pos)


def _parse_phrase(text: str, pos: int) -> tuple[str, int]:
    """Parse a display-name ``phrase``: one or more ``word`` tokens.

    Multiple words are joined with single spaces. Per RFC 5322 a phrase is a
    sequence of words, so ``"John" Doe`` parses to the display name
    ``"John Doe"``.
    """
    parts: list[str] = []
    first = True
    while True:
        save = pos
        pos = _skip_cfws(text, pos)
        if pos >= len(text):
            if first:
                raise _ParseError("expected phrase")
            break
        ch = text[pos]
        if not (ch == '"' or ch in _ATEXT_CHARS):
            if first:
                raise _ParseError("expected phrase")
            pos = save
            break
        word, pos = _parse_word(text, pos)
        parts.append(word)
        first = False
        if pos >= len(text):
            break
    return " ".join(parts), pos


def parse_mailbox(text: str) -> Mailbox:
    """Parse a single RFC 5322 mailbox specification.

    Accepts both the bare ``local-part@domain`` form and the bracketed
    display-name form ``Display Name <local-part@domain>``. Comments and
    folding whitespace are tolerated wherever RFC 5322 permits. Returns a
    :class:`Mailbox` with the display name (or ``None``), the local part,
    and the domain.

    Raises:
        ValueError: on any unrecoverable syntax violation.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    text = text.strip()
    if not text:
        raise ValueError("empty input")
    pos = 0
    display_name: str | None = None

    # Look ahead (skipping CFWS) for an angle bracket. If found, everything
    # before it is the display name. Otherwise we treat the whole string as
    # a bare addr-spec.
    probe = _skip_cfws(text, 0)
    if probe < len(text) and text[probe] == "<":
        bare = False
    else:
        try:
            lt = text.index("<")
        except ValueError:
            bare = True
        else:
            bare = False
            # If we reach here, there's a '<' but not at the start. Parse it
            # as a phrase + angle-addr below by passing the full text through.
            # The only ambiguity: a stray '<' inside an unquoted local-part
            # is not valid atext anyway, so this is safe.

    if not bare:
        if probe < len(text) and text[probe] != "<":
            display_name, pos = _parse_phrase(text, 0)
            pos = _skip_cfws(text, pos)
        if pos >= len(text) or text[pos] != "<":
            raise ValueError("expected '<' before addr-spec")
        pos += 1
        local_part, pos = _parse_word(text, pos)
        pos = _skip_cfws(text, pos)
        if pos >= len(text) or text[pos] != "@":
            raise ValueError("expected '@' in addr-spec")
        pos += 1
        pos = _skip_cfws(text, pos)
        domain, pos = _parse_dot_atom(text, pos)
        pos = _skip_cfws(text, pos)
        if pos >= len(text) or text[pos] != ">":
            raise ValueError("expected '>' to close angle-addr")
        pos += 1
        pos = _skip_cfws(text, pos)
        if pos != len(text):
            raise ValueError("trailing characters after '>'")
        return Mailbox(display_name=display_name, local_part=local_part, domain=domain)

    local_part, pos = _parse_word(text, 0)
    pos = _skip_cfws(text, pos)
    if pos >= len(text) or text[pos] != "@":
        raise ValueError("expected '@' in addr-spec")
    pos += 1
    pos = _skip_cfws(text, pos)
    domain, pos = _parse_dot_atom(text, pos)
    pos = _skip_cfws(text, pos)
    if pos != len(text):
        raise ValueError("trailing characters after addr-spec")
    return Mailbox(display_name=None, local_part=local_part, domain=domain)
