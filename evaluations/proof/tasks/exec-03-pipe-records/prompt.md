Write `solution.py` with one function:

```python
def parse(text: str) -> list[list[str]]:
```

It parses text in a pipe-separated record format and returns one list of field strings per record.

Rules:

1. A line break is LF (`\n`) or the pair CRLF (`\r\n`). A CR that is not immediately followed by LF is an ordinary character.
2. Outside quotes, a line break ends the current record. A line break at the very end of the text ends the last record and does not start another one. The last record does not need a line break.
3. If a line break appears exactly where a record would start (at the start of the text, or right after the line break that ended the previous record), that line is empty. An empty line is skipped and produces no record. Only a line with zero characters is empty. A line of only spaces or tabs is a record with one field, which rule 5 turns into `""`. `parse("")` returns `[]`.
4. Outside quotes, `|` separates fields. A record with k separators has k + 1 fields, so the line `a|` is the record `["a", ""]`.
5. An unquoted field is its raw text with leading and trailing spaces and tabs removed. No other character is removed. A `"` that is not the first character of a field, after any spaces and tabs, is an ordinary character.
6. A field is quoted when its first character other than space or tab is `"`. The spaces and tabs before that opening quote are ignored. Read the characters after the opening quote from left to right: the pair `""` stands for one `"` character, and any other `"` is the closing quote. The field's value is every character between the opening and closing quote, kept exactly. `|`, CR, LF, spaces and tabs inside the quotes are part of the value.
7. After the closing quote, only spaces and tabs may appear before the next `|`, line break, or end of text. They are ignored. Any other character there raises `ValueError`.
8. Text that ends inside a quoted field (no closing quote) raises `ValueError`.

Examples:

```python
parse('a|b|c\nd|"e|f"|\n')
# [['a', 'b', 'c'], ['d', 'e|f', '']]

parse('x |"say ""hi""" \r\n\r\n"two\nlines"')
# [['x', 'say "hi"'], ['two\nlines']]

parse('"open')
# raises ValueError
```

Use the Python standard library only.
