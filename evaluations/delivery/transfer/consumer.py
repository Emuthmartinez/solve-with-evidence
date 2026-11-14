"""Independent consumer for a packet reader's UTF-8 byte map."""
import json
import sys

# Signal-log specification. A wire tag includes a literal backslash and quote.
RECORDS = [('μ', 'n\t'), ('Q\\"', '雪'), ('e', 'e\u0301'), ('E', '🪁\r\n'), ('/', ''), ('μ', 'Ω')]
READS = [(0, 3), (3, 7), (8, 12), (16, 17), (17, 17), (21, 24)]


def mapped(records):
    wire = ''
    spans = []
    for record, (tag, text) in enumerate(records):
        wire += tag + ':'
        start = len(wire.encode('utf-8'))
        wire += text
        spans.append({'record': record, 'begin': start, 'end': len(wire.encode('utf-8'))})
        wire += '\x1e'
    return wire, spans


def select(spans, lo, hi, inclusive=False):
    pick = []
    for s in spans:
        left, right = max(lo, s['begin']), min(hi, s['end'])
        if (left <= right if inclusive else left < right):
            pick.append(s['record'])
    return pick


def obj(value, keys):
    return isinstance(value, dict) and set(value) == set(keys)


def same(left, right):
    # The numeric fields require JSON integers. True and 1 compare equal in Python.
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def verify(payload):
    if not obj(payload, ['packet', 'proof']):
        return False
    packet, proof = payload['packet'], payload['proof']
    if not obj(packet, ['wire', 'payloads', 'reads']) or not obj(proof, ['input', 'strict', 'inclusive']):
        return False
    wire, spans = mapped(RECORDS)
    result = {'wire':wire, 'payloads':spans, 'reads':[select(spans, *r) for r in READS]}
    if not same(packet, result) or not obj(proof['input'], ['window']):
        return False
    window = proof['input']['window']
    if not isinstance(window, list) or len(window) != 2 or not all(type(p) is int for p in window):
        return False
    lo, hi = window
    if not (0 <= lo < hi <= len(wire.encode('utf-8'))) or (lo, hi) in READS:
        return False
    strict = select(spans, lo, hi)
    faulty = select(spans, lo, hi, True)
    return bool(strict) and strict != faulty and same(proof['strict'], strict) and same(proof['inclusive'], faulty)


def unique(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError('duplicate key')
    return obj


def decode(raw):
    def nonfinite(_):
        raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)


if __name__ == '__main__':
    if sys.argv[1:] != ['packet-map']:
        sys.exit(2)
    try:
        accepted = verify(decode(sys.stdin.buffer.read()))
    except (ValueError, RecursionError):
        accepted = False
    if not accepted:
        print('packet, wire, byte map, reads or discriminating proof failed', file=sys.stderr)
    sys.exit(0 if accepted else 1)
