# Mailbox Address Parser

Parses RFC 5322 mailbox address specifications into a `Mailbox(display_name, local_part, domain)`. Handles display names, quoted local-parts (including backslash escapes), comments, and folding whitespace.

## Usage

```python
from mailbox_address_parser import parse_mailbox

m = parse_mailbox('"Alice \\"Bob" <alice@example.org>')
print(m.display_name)  # Alice "Bob
print(m.local_part)    # alice
print(m.domain)        # example.org
```

## Exports

- `parse_mailbox(text: str) -> Mailbox` — parse a single mailbox.
- `Mailbox` — frozen dataclass with `display_name: str | None`, `local_part: str`, `domain: str`.

## Why this exists

Email headers are full of comments, quoted strings, and folding whitespace that a naive `split('@')` mangles. This library gives you a correct parse of one mailbox at a time. The trade-off: it only handles a single mailbox per call, not comma-separated address lists (`addr-spec` lists are a separate production in RFC 5322 and come with their own quoting rules around commas).

## Edge cases you will hit

- A display name containing a comma must be quoted, but commas are valid inside quoted local-parts and display names. This parser does not split on commas — call it once per mailbox.
- Domain literals (`user@[127.0.0.1]`) are not supported; only dot-atom domains are.
- Comments are discarded entirely; they are not preserved on the returned `Mailbox`.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

