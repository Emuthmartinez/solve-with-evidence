# Halvard Bank: account transaction export (CSV)

Format version 3.2. This document describes the nightly transaction export that Halvard Bank
delivers to corporate clients over SFTP.

## Overview

One export covers every sub-account of a multi-currency client account for one business day, so a
single file can mix currencies. Each transaction appears as one data record. The file opens with a
header line and closes with a trailer line that lets the client confirm the file arrived complete.

## Encoding and line ends

Files are encoded in UTF-8. Some delivery channels put a byte-order mark (the bytes EF BB BF) at the
start of the file and others do not, so readers must accept both. Lines end in CR LF or in LF alone,
again depending on the channel. The last line of the file may or may not end with a line break.
A file never contains an empty line. An empty line anywhere in the file, including after the
trailer, makes the file invalid.

## Layout

The first line of the file is the header, which is always exactly:

    Booking date;Value date;Reference;Status;Amount;Currency;Memo

Then come the data records, one per transaction, in the order the bank's systems produced them. A day
without transactions has no data records. The last line of the file is the trailer, described below.
Every file has exactly one trailer. A file whose last line is not a trailer was cut off in transfer:
it is invalid as a whole, even when every record in it is valid. Nothing may follow the trailer.

## Fields

Fields are separated by semicolons, and every data record has exactly seven fields, in the order of
the header. A field that contains a semicolon, a double quote or a line break is enclosed in double
quotes, and a double quote inside it is written twice, as in RFC 4180. For example, the memo
`Invoice "A-7"; final` is written `"Invoice ""A-7""; final"`. Any field may be quoted; the quotes are
not part of its value. Values carry no padding.

A memo may contain a line break. The record then continues on the next physical line, and it is still
one data record: one transaction, counted once in the trailer. Inside a memo the bank always writes
a line break as a single LF character, whatever line ends the rest of the file uses. The line break
is part of the memo.

### Booking date and Value date

Dates are written day first, as DD.MM.YYYY with a two-digit day and month: 05.03.2026 is the fifth of
March 2026. A date that does not exist in the calendar, such as 30.02.2026, makes the file invalid.
The booking date is always present. The value date is empty when the bank has not fixed it yet, which
is usual for pending records.

### Reference

The bank's identifier for the transaction. It is never empty. References are compared exactly,
character for character.

### Status

`B` for a booked transaction, `P` for a pending one. No other value occurs in a valid file.

### Amount

Amounts use continental notation, and the decimal mark is a comma. The integer part is written
either as plain digits (`1234567`) or with a dot between groups of three digits (`1.234.567`). With
dots, the first group has one to three digits and every later group exactly three; any other use of
the dot is invalid. The dot never marks decimals: `1.234` is one thousand two hundred thirty-four in
every currency. A credit has no sign. A debit has a minus sign after the number, as in `12,50-`. No
other sign is used, before or after the number.

How many decimals an amount may have depends on its currency: at most the number of decimals of the
currency's minor unit (two for EUR, none for JPY, three for KWD). The bank often writes fewer, and
missing decimals are zeros: `7` and `7,5` are valid EUR amounts, worth 7,00 and 7,50 EUR. When a
comma is present, at least one digit follows it. An amount with more decimals than its currency
allows is invalid, whatever the digits: `1,234` is not a valid EUR amount, and `1,5` is not a valid
JPY amount.

An amount has at most 18 digits, counting integer and decimal digits but not dots. Amounts near this
limit occur on treasury and securities settlement accounts. Clients must convert every amount
exactly; a rounded amount breaks reconciliation.

### Currency

The ISO 4217 code of the sub-account's currency. The bank uses only the currencies in the currency
table supplied with this document, which also gives each currency's number of decimals. A record in
any other currency makes the file invalid.

## Pending and booked records

A card payment or an incoming transfer is often reported as pending (status `P`) before it is booked
(status `B`). Both records carry the same reference. Because the export is assembled from several
systems, the booked record can come before or after the pending one in the same file.

A pending record is superseded when the file also contains a booked record with the same reference,
anywhere in the file, earlier or later. Readers drop a superseded record and keep the booked one.
The two records may differ in amount and dates: a card authorisation of 50,00 is often booked as
47,30. A pending record without a booked record in the same file stays pending; the bank will
report it as booked in a later file. Readers deliver the records they keep in file order.

Within one file a reference occurs at most once as booked and at most once as pending. A file in
which a reference occurs twice with the same status is invalid. A superseded record is still part of
the file, and the rules for its fields apply to it as to any other record.

## Trailer

The trailer has three fields: the letter `T`, the record count and the hash total, as in
`T;152;48.211,07-`.

The record count is the number of data records in the file, superseded records included, written in
plain digits. A record whose memo spans several physical lines counts once.

The hash total is the sum of the Amount fields of all data records, superseded records included,
taken as signed numbers. Currencies are ignored: the hash total adds the numbers as written, so
records of 1,50 EUR, 1.234 JPY and 0,250- KWD add up to 1.235,25. The hash total is written in the
amount notation above, without its limits: it may have any number of digits and decimals. Readers
compare it as a number, so `1.235,25`, `1235,25` and `1235,250` are the same hash total.

A file whose record count or hash total does not match its data records is invalid.

## Rejecting a file

A client must reject an invalid file as a whole and import nothing from it. The bank sends a
corrected file on request.
