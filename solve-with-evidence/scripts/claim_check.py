"""Map each sentence of a prose deliverable to a source passage, or flag it.

Every number, name and quotation must appear in the sources, and every sentence must
share enough wording with one passage. A mapping shows where a claim could come from.
It does not show that the passage supports the claim: "grew 20%" maps to "fell 20%".
Read each mapped pair, or have an independent reviewer read it, before relying on it.
"""
import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

STOP = frozenset("""a about above after again all also am an and any are as at be because been before
being below between both but by can could did do does doing down during each few for from further
had has have having he her here hers him his how i if in into is it its just me more most my no nor
not now of off on once only or other our ours out over own same she should so some such than that
the their theirs them then there these they this those through to too under until up very was we
were what when where which while who whom why will with would you your yours""".split())
ABBREVIATIONS = frozenset('mr mrs ms dr st vs etc inc ltd co no approx e.g i.e fig jr sr'.split())
CONNECTORS = frozenset('of de la van von der del da di'.split())
# shortcut: "one" is skipped because it is usually a pronoun; ordinals and words such as
# "twice" or "half" are not parsed. Upgrade if a deliverable relies on them.
WORDS = dict(zip('zero two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                 'fifteen sixteen seventeen eighteen nineteen'.split(), [0, *range(2, 20)]))
TENS = dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(), range(20, 100, 10)))
UNITS = dict(zip('one two three four five six seven eight nine'.split(), range(1, 10)))
SCALES = {'hundred': 100, 'thousand': 10**3, 'million': 10**6, 'billion': 10**9, 'trillion': 10**12,
          'k': 10**3, 'm': 10**6, 'b': 10**9}
NUMBER = re.compile(
    r'(?<![\w.])(?:(?P<digits>\d+(?:,\d{3})*(?:\.\d+)*)(?P<suffix>(?-i:[kKMB])(?!\w))?'
    r'|(?P<tens>%s)(?:-(?P<unit>%s))?\b|(?P<word>%s)\b)'
    r'(?:\s+(?P<scale>hundred|thousand|million|billion|trillion)\b)?(?P<percent>\s?%%|\s+percent\b)?' % ('|'.join(TENS), '|'.join(UNITS), '|'.join(WORDS)),
    re.IGNORECASE)
QUOTE = re.compile(r'["“]([^"“”]+)["”]')
IDENTIFIER = re.compile(r'https?://\S+|[@#]\w+|\b\d{1,2}:\d{2}\b|\b\d{4}-\d{2}-\d{2}\b|\b\w+(?:[._/-]\w+)*\.[a-z]{2,4}\b'
                        r'|\b[A-Za-z]+[-.]?\d[\w.-]*|\b[a-z]+[A-Z]\w*|\b\w+_\w+\b')
WORD = re.compile(r"[A-Za-z][\w'’-]*")
BOUNDARY = re.compile(r'[.!?]["”’)\]]*\s+(?=["“‘(\[]?[A-Z0-9@#$])')
MIDCAP = re.compile(r"(?<=[a-z,;:] )[A-Z][\w'’-]+")


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower().replace('’', "'").replace("'s ", ' '))


def stem(word):
    for suffix in ('ies', 'ing', 'ed', 'es', 's'):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[:-len(suffix)] + ('y' if suffix == 'ies' else '')
            break
    if len(word) > 3 and word[-1] == word[-2]:
        word = word[:-1]
    return word[:-1] if len(word) > 3 and word.endswith('e') else word


def ordered_terms(text):
    return [stem(t) for t in tokens(text) if t not in STOP and not t.isdigit() and len(t) > 1]


def terms(text):
    return set(ordered_terms(text))


def numbers(text):
    """Yield (key, match) for each number; key is (canonical value, is_percent)."""
    for m in NUMBER.finditer(text):
        if m['digits']:
            raw = m['digits'].replace(',', '')
            if raw.count('.') > 1:
                value = raw  # a version such as 0.166.0 is compared as written
            else:
                value = Decimal(raw) * SCALES.get((m['suffix'] or '').lower(), 1)
        elif m['tens']:
            value = Decimal(TENS[m['tens'].lower()] + UNITS.get((m['unit'] or '').lower(), 0))
        else:
            value = Decimal(WORDS[m['word'].lower()])
        if m['scale'] and not isinstance(value, str):
            value *= SCALES[m['scale'].lower()]
        key = value if isinstance(value, str) else format(value.normalize(), 'f')
        yield (key, bool(m['percent'])), m


def blocks(text, skip_code=False):
    """Yield (line number, text, is_heading) for each paragraph, list item, table row or heading."""
    current, start, fenced = [], 0, False
    for number, line in enumerate(text.splitlines() + [''], 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            fenced = not fenced
            stripped = ''
        if fenced and skip_code:
            continue
        opener = re.match(r'(#+|[-*+>]|\d+[.)]|\|)\s*', stripped)
        if current and (not stripped or opener):
            yield start, '\n'.join(current), False  # line breaks are kept so a flag can name its line
            current = []
        if not stripped:
            continue
        clean = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', stripped)
        clean = re.sub(r'[*`|]+', ' ', clean[opener.end():] if opener else clean).strip()
        if opener and opener[1].startswith('#'):
            if clean:
                yield number, clean, True
        elif clean:
            if not current:
                start = number
            current.append(clean)


def sentences(text):
    """Yield (lines before the sentence, sentence on one line)."""
    start = 0
    for m in list(BOUNDARY.finditer(text)) + [None]:
        end = m.end() if m else len(text)
        before = re.search(r'([A-Za-z.]+)\.$', text[start:m.start() + 1]) if m else None
        if before and (before[1].lower() in ABBREVIATIONS or len(before[1]) == 1):
            continue
        if text[start:end].strip():
            lead = len(text[start:end]) - len(text[start:end].lstrip())
            yield text[:start + lead].count('\n'), ' '.join(text[start:end].split())
        start = end


def names(sentence, midcaps, known):
    """Yield (type, text) for runs of capitalised words. Punctuation and digits end a run."""
    words = [(re.sub(r"['’]s$", '', m[0]), m.start(), m.end()) for m in WORD.finditer(sentence)]
    runs, run = [], []
    for index, (word, start, end) in enumerate(words):
        gap = sentence[words[index - 1][2]:start] if index else ''
        if run and gap.strip(' &'):
            runs.append(run)
            run = []
        following = words[index + 1] if index + 1 < len(words) else ('', end, end)
        bridge = (run and word.lower() in CONNECTORS and following[0][:1].isupper()
                  and not sentence[end:following[1]].strip())
        if (word[:1].isupper() and len(word) > 1) or bridge:
            # A capital at the start of a sentence, or after a colon, may be only position.
            run.append((word, not run and (index == 0 or ':' in gap)))
        elif run:
            runs.append(run)
            run = []
    for run in runs + [run]:
        opens = bool(run) and run[0][1]
        while run and run[0][0].lower() in STOP:
            run, opens = run[1:], False
        if opens and run[0][0] not in midcaps and not run[0][0].isupper():
            if run[0][0].lower() not in known and len(run) == 1:
                yield 'possible name', run[0][0]
            if run[0][0].lower() in known or len(run) == 1:
                run = run[1:]
        while run and run[0][0].lower() in STOP:
            run = run[1:]
        if run:
            yield 'name', ' '.join(word for word, _ in run)


def facts(sentence, heading, midcaps, known):
    """Return [(type, display, key, context)] for the quotations, names and numbers in a sentence.

    A number's context is the wording around it. A source passage must hold the number beside
    that wording, so "2 days" is not supported by a passage about "two clinics".
    """
    found = []

    def take(pattern, kind, keep=lambda m: True, group=0):
        nonlocal sentence
        for m in list(pattern.finditer(sentence)):
            if keep(m):
                found.append((kind, m[group].strip(), ' '.join(tokens(m[group])), None))
        sentence = pattern.sub(lambda m: ' ' * len(m[0]) if keep(m) else m[0], sentence)

    take(QUOTE, 'quote', lambda m: len(m[1].split()) >= 3, group=1)
    take(IDENTIFIER, 'name')
    if not heading:
        found += [(kind, name, ' '.join(tokens(name)), None) for kind, name in names(sentence, midcaps, known)]
    for key, m in numbers(sentence):
        before, after = ordered_terms(sentence[:m.start()]), ordered_terms(sentence[m.end():])
        unit = re.match(r'\s+([A-Za-z]+)', sentence[m.end():])
        if unit and unit[1].lower() not in STOP:
            context = set(after[:2])  # "47 additional clinics": the unit phrase must be in the passage
        else:
            context = set(before[-2:] + after[:2])
        found.append(('number', m[0].strip() + (unit[0] if unit else ''), key, context))
    return found


def check(deliverable, sources, min_overlap=0.4):
    """sources: iterable of (name, text). Returns the report dictionary."""
    pool = []
    for name, text in sources:
        for line, passage, _ in blocks(text):
            passage = ' '.join(passage.split())
            pool.append({'source': name, 'line': line, 'text': passage, 'terms': terms(passage),
                         'words': ' %s ' % ' '.join(tokens(passage)),
                         'numbers': {key for key, _ in numbers(IDENTIFIER.sub(' ', passage))}})
    midcaps = set(MIDCAP.findall(deliverable))
    known = set(re.findall(r'\b[a-z]+\b', deliverable))
    for _, text in sources:
        midcaps.update(MIDCAP.findall(text))
        known.update(tokens(text))
    report = {'outcome': 'all_mapped', 'sentences': 0, 'mapped': 0, 'skipped': 0, 'flags': [], 'map': []}
    for line, block, heading in blocks(deliverable, skip_code=True):
        for offset, sentence in sentences(block):
            report['sentences'] += 1
            wanted = terms(sentence)
            found = facts(sentence, heading, midcaps, known)
            missing, doubtful = [], []
            for kind, display, key, context in found:
                if kind == 'number':
                    holders = [p for p in pool if key in p['numbers']]
                    if not holders:
                        missing.append({'type': kind, 'text': display, 'reason': 'not in any source'})
                    elif context and not any(context & p['terms'] for p in holders):
                        missing.append({'type': kind, 'text': display,
                                        'reason': 'in the sources only in another context'})
                elif kind == 'possible name':
                    if len(wanted) >= 3:
                        doubtful.append({'type': kind, 'text': display, 'reason': 'not in any source'})
                elif not any(' %s ' % key in p['words'] for p in pool):
                    missing.append({'type': kind, 'text': display, 'reason': 'not in any source'})
            overlap, best = max(((len(wanted & p['terms']) / len(wanted) if wanted else 1.0, i)
                                 for i, p in enumerate(pool)), default=(0.0, None))
            nearest = None if best is None else {k: pool[best][k] for k in ('source', 'line', 'text')}
            entry = {'line': line + offset, 'sentence': sentence, 'overlap': round(overlap, 2), 'nearest': nearest}
            if missing:
                report['flags'].append({**entry, 'kind': 'unsupported', 'items': missing})
            elif doubtful or (len(wanted) >= 3 and overlap < min_overlap):
                report['flags'].append({**entry, 'kind': 'unmatched', 'items': doubtful})
            elif len(wanted) < 3 and all(kind == 'possible name' for kind, *_ in found):
                report['skipped'] += 1
            else:
                report['mapped'] += 1
                report['map'].append(entry)
    if report['flags']:
        report['outcome'] = 'flagged'
    return report


def read_sources(paths):
    for path in paths:
        files = sorted(p for p in path.rglob('*') if p.suffix in ('.md', '.txt')) if path.is_dir() else [path]
        for file in files:
            yield str(file), file.read_text(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('deliverable', type=Path, help='prose file to check')
    parser.add_argument('--source', type=Path, action='append', required=True,
                        help='source file, or directory of .md and .txt files; repeatable')
    parser.add_argument('--min-overlap', type=float, default=0.4,
                        help='share of a sentence\'s content words one passage must contain (default 0.4, uncalibrated)')
    parser.add_argument('--json', action='store_true', help='print the full report as JSON')
    args = parser.parse_args()
    try:
        report = check(args.deliverable.read_text(encoding='utf-8'), list(read_sources(args.source)),
                       args.min_overlap)
    except (OSError, UnicodeDecodeError) as exc:
        print(f'claim check unavailable: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for flag in report['flags']:
            why = '; '.join(f"{i['type']} \"{i['text']}\" {i['reason']}" for i in flag['items'])
            print(f"FLAG {flag['kind']} line {flag['line']}: {why or 'no passage shares enough wording'}"
                  f"\n  {flag['sentence']}")
        print(f"{report['mapped']} of {report['sentences']} sentences mapped, {len(report['flags'])} flagged, "
              f"{report['skipped']} too short to check.")
    return 1 if report['flags'] else 0


if __name__ == '__main__':
    sys.exit(main())
