# exec-01-bank-import: fairness notes

The solver never sees this file, the grader or the exemplars.

## What the task is

Make `importer.load(path)` follow the bank's format description, `docs/FORMAT.md`, inside an existing package, without breaking the other caller of the shared amount parser.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the rules are vendor prose spread over the sections of `FORMAT.md`, and several only matter together: the trailer counts and adds superseded records, the hash total adds values across currencies with different exponents, and the dot is a thousands separator whose placement is constrained. `README.md` says that `money.parse_amount` is shared with `statement.parse_adjustment`, which parses English notation, so the obvious fix to `parse_amount` breaks a caller nobody runs. The sample loads under many wrong readers: every amount in it has full decimals and dots, it has no 18-digit amount, no file without a byte-order mark, no empty export, and no record whose booked row comes before the pending one is checked by `test_reader.py`. The two visible tests pass on the starter, on every variant and on the bad exemplar. Nothing in the prompt says which rules a reader is likely to break.

## What the bad exemplar does

It is the first version a quick solver writes after the sample stops crashing: the `csv` module with `utf-8-sig`, `money.parse_amount` switched to the bank's notation in place (dots dropped, comma to dot, through `float`), empty rows skipped, the trailer skipped rather than checked, a booked record dropping only the pending records before it, and `datetime.strptime` errors left as `ValueError`. It passes `test_reader.py`.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| the sample loads | "Make `importer.load(path)` import every file that follows `docs/FORMAT.md`"; the sample is "a real export". The expected rows follow from the rules below | `prompt.md`; `data/export-sample.csv` |
| english adjustments still parse | "Everything else in the package must keep working as documented." `parse_adjustment` parses "'1,234.56 EUR' or '-12.5 EUR'"; `parse_amount` "is shared by the reader and by `importer/statement.py`" | `prompt.md`; `statement.py` docstring; `README.md` |
| an 18-digit amount converts exactly | "An amount has at most 18 digits ... Clients must convert every amount exactly" | `FORMAT.md`, Amount |
| the hash total is compared exactly | "A file whose record count or hash total does not match its data records is invalid"; the hash total "may have any number of digits and decimals" and readers "compare it as a number" | `FORMAT.md`, Trailer |
| the hash total adds amounts across currencies | "Currencies are ignored: the hash total adds the numbers as written, so records of 1,50 EUR, 1.234 JPY and 0,250- KWD add up to 1.235,25." | `FORMAT.md`, Trailer |
| a dot groups thousands in every currency | "The dot never marks decimals: `1.234` is one thousand two hundred thirty-four in every currency." | `FORMAT.md`, Amount |
| missing decimals are zeros | "at most the number of decimals of the currency's minor unit (two for EUR, none for JPY, three for KWD) ... missing decimals are zeros: `7` and `7,5` are valid EUR amounts" | `FORMAT.md`, Amount; `data/currencies.csv` |
| more decimals than the currency allows is an error | "An amount with more decimals than its currency allows is invalid ... `1,234` is not a valid EUR amount, and `1,5` is not a valid JPY amount." | `FORMAT.md`, Amount |
| a misplaced dot is an error | "With dots, the first group has one to three digits and every later group exactly three; any other use of the dot is invalid." | `FORMAT.md`, Amount |
| a sign before the number is an error | "A credit has no sign. A debit has a minus sign after the number ... No other sign is used, before or after the number." | `FORMAT.md`, Amount |
| more than 18 digits is an error | "An amount has at most 18 digits, counting integer and decimal digits but not dots." | `FORMAT.md`, Amount |
| a pending record superseded by a later booked one is dropped | "A pending record is superseded when the file also contains a booked record with the same reference, anywhere in the file, earlier or later. Readers drop a superseded record" | `FORMAT.md`, Pending and booked records |
| a pending record superseded by an earlier booked one is dropped | The same sentence | `FORMAT.md`, Pending and booked records |
| a pending record never booked is kept in file order | "A pending record without a booked record in the same file stays pending ... Readers deliver the records they keep in file order." | `FORMAT.md`, Pending and booked records; `load` docstring |
| a reference twice with one status is an error | "A file in which a reference occurs twice with the same status is invalid." | `FORMAT.md`, Pending and booked records |
| a missing trailer is an error | "Every file has exactly one trailer. A file whose last line is not a trailer was cut off in transfer: it is invalid as a whole" | `FORMAT.md`, Layout |
| a wrong record count is an error | "The record count is the number of data records in the file"; "A file whose record count ... does not match its data records is invalid." | `FORMAT.md`, Trailer |
| a wrong hash total is an error | "The hash total is the sum of the Amount fields ... taken as signed numbers"; a mismatch is invalid | `FORMAT.md`, Trailer |
| nothing may follow the trailer | "Nothing may follow the trailer." and "An empty line anywhere in the file, including after the trailer, makes the file invalid." | `FORMAT.md`, Layout; Encoding and line ends |
| the trailer counts and adds superseded records | "the number of data records in the file, superseded records included"; the hash total adds "all data records, superseded records included" | `FORMAT.md`, Trailer |
| a quoted memo keeps its semicolon and quotes | "a double quote inside it is written twice, as in RFC 4180 ... `Invoice "A-7"; final` is written `"Invoice ""A-7""; final"`" | `FORMAT.md`, Fields |
| a memo with a line break is one record | "The record then continues on the next physical line, and it is still one data record ... The line break is part of the memo." Written as "a single LF character" | `FORMAT.md`, Fields |
| a file without byte-order mark or CR loads | "readers must accept both"; "Lines end in CR LF or in LF alone"; "The last line of the file may or may not end with a line break." | `FORMAT.md`, Encoding and line ends |
| an empty value date is None | "The value date is empty when the bank has not fixed it yet"; `value_date` "or None when the bank left it empty" | `FORMAT.md`, Booking date and Value date; `importer/model.py` |
| an impossible date is an error | "A date that does not exist in the calendar, such as 30.02.2026, makes the file invalid." Every violation raises `FormatError` | `FORMAT.md`; `prompt.md`; `load` docstring |
| an unknown status is an error | "`B` for a booked transaction, `P` for a pending one. No other value occurs in a valid file." | `FORMAT.md`, Status |
| an export with no records loads as an empty list | "A day without transactions has no data records." The record count and hash total of no records are 0 | `FORMAT.md`, Layout; Trailer |
| a file that is not UTF-8 is an error | "a file that holds bytes that are not valid UTF-8 is invalid" and "raise `FormatError` for every file that breaks it". The files hold `Café` in Latin-1, whose byte E9 is not UTF-8. The same memo in UTF-8 loads | `FORMAT.md`, Encoding and line ends; `prompt.md` |
| a double quote outside the quoting rules is an error | "A double quote occurs nowhere else: one in a field that is not enclosed in quotes, or text between a closing quote and the next separator, makes the file invalid." The memo `"Invoice A-7" final` has text after its closing quote, and the memo `Invoice "A-7" final` holds a double quote without being enclosed | `FORMAT.md`, Fields |
| a line that ends in CR alone is an error | "A CR without an LF after it is not a line end, and a file whose lines end that way is invalid." | `FORMAT.md`, Encoding and line ends |

The last three checks reject files that Python's `csv` module and text mode accept. `csv.reader` reads `"Invoice A-7" final` as `Invoice A-7 final`, keeps a double quote in a field that is not quoted, and takes a lone CR for a line end. Decoding a Latin-1 byte raises `UnicodeDecodeError`, which is not a `FormatError`. The good exemplar therefore splits lines and fields itself. `FORMAT.md` states each of the three rules in a sentence of its own, as it does for an empty line and a misplaced dot. The checks stay away from what it leaves open: a CR inside a memo, a file that mixes CR LF and LF, and quotes around a header or trailer field.

The grader writes every hidden file into its own temporary folder and reads the sample from the task's workspace copy, not from the work directory. The expected sample rows are the good exemplar's output, stored as a count and a sha256 of their `repr`.

`variants/exec-01-bank-import.py` holds one plausible mistake per rule. `test_bench.py` checks that each fails exactly the checks it lists.
