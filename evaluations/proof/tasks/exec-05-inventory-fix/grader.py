import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises


def row(on_hand, reserved):
    return {'on_hand': on_hand, 'reserved': reserved, 'available': on_hand - reserved}


def stocked(s):
    """apple: 10 on hand, order o1 holds 4. pear: 2 on hand, nothing held."""
    inv = s.Inventory()
    inv.restock('apple', 10)
    inv.restock('pear', 2)
    inv.reserve('o1', 'apple', 4)
    return inv


def state(inv):
    return (copy.deepcopy(inv.snapshot()), inv.reservation('o1', 'apple'), inv.reservation('o1', 'pear'))


def unchanged_after_error(s, error, call):
    """call(inv) must raise `error` and leave the inventory as it was."""
    inv = stocked(s)
    before = state(inv)
    return raises(error, call, inv) and state(inv) == before


def restock_twice(s):
    inv = s.Inventory()
    inv.restock('apple', 5)
    inv.restock('apple', 3)
    return inv.available('apple') == 8 and inv.snapshot() == {'apple': row(8, 0)}


def reserve_counts_existing(s):
    inv = stocked(s)
    before = state(inv)
    return raises(ValueError, inv.reserve, 'o2', 'apple', 7) and state(inv) == before


def reserve_all_available(s):
    inv = stocked(s)
    inv.reserve('o2', 'apple', 6)
    return inv.available('apple') == 0 and inv.reservation('o2', 'apple') == 6


def reserve_adds(s):
    inv = stocked(s)
    inv.reserve('o1', 'apple', 3)
    return inv.reservation('o1', 'apple') == 7 and inv.snapshot()['apple'] == row(10, 7)


def reservations_per_sku(s):
    inv = stocked(s)
    inv.reserve('o1', 'pear', 1)
    return inv.reservation('o1', 'apple') == 4 and inv.reservation('o1', 'pear') == 1


def release_returns_and_frees(s):
    inv = stocked(s)
    return (inv.release('o1', 'apple') == 4 and inv.available('apple') == 10
            and inv.reservation('o1', 'apple') == 0)


def release_twice(s):
    inv = stocked(s)
    inv.release('o1', 'apple')
    return raises(KeyError, inv.release, 'o1', 'apple')


def ship_lowers_both(s):
    inv = stocked(s)
    inv.ship('o1', 'apple', 3)
    return inv.snapshot()['apple'] == row(7, 1) and inv.reservation('o1', 'apple') == 1


def ship_to_zero_removes(s):
    inv = stocked(s)
    inv.ship('o1', 'apple', 4)
    return (inv.reservation('o1', 'apple') == 0 and inv.snapshot()['apple'] == row(6, 0)
            and raises(KeyError, inv.release, 'o1', 'apple'))


def snapshot_sorted(s):
    inv = s.Inventory()
    for sku in ('pear', 'apple', 'fig'):
        inv.restock(sku, 1)
    return list(inv.snapshot()) == ['apple', 'fig', 'pear']


def snapshot_inner_copy(s):
    inv = stocked(s)
    snap = inv.snapshot()
    snap['apple']['on_hand'] = 99
    snap['apple']['reserved'] = 0
    snap['apple']['extra'] = 1
    return inv.snapshot() == {'apple': row(10, 4), 'pear': row(2, 0)} and inv.available('apple') == 6


def snapshot_outer_copy(s):
    inv = stocked(s)
    del inv.snapshot()['pear']
    return list(inv.snapshot()) == ['apple', 'pear']


def zero_restock_creates_nothing(s):
    inv = s.Inventory()
    return raises(ValueError, inv.restock, 'kiwi', 0) and inv.snapshot() == {}


CHECKS = [
    ('1: new inventory snapshot is empty', lambda s: s.Inventory().snapshot() == {}),
    ('2: restock 0 raises and changes nothing', lambda s: unchanged_after_error(s, ValueError, lambda i: i.restock('apple', 0))),
    ('2: restock 0 of a new sku creates nothing', zero_restock_creates_nothing),
    ('2: restock negative raises', lambda s: unchanged_after_error(s, ValueError, lambda i: i.restock('apple', -2))),
    ('2: restock float raises', lambda s: unchanged_after_error(s, ValueError, lambda i: i.restock('apple', 2.5))),
    ('2: reserve 0 raises and changes nothing', lambda s: unchanged_after_error(s, ValueError, lambda i: i.reserve('o1', 'apple', 0))),
    ('2: reserve str raises', lambda s: unchanged_after_error(s, ValueError, lambda i: i.reserve('o1', 'apple', '1'))),
    ('2: ship 0 raises and changes nothing', lambda s: unchanged_after_error(s, ValueError, lambda i: i.ship('o1', 'apple', 0))),
    ('2: ship negative raises', lambda s: unchanged_after_error(s, ValueError, lambda i: i.ship('o1', 'apple', -1))),
    ('3: restock adds to existing stock', restock_twice),
    ('3: first restock starts from zero', lambda s: (lambda i: (i.restock('fig', 4), i.snapshot())[1])(s.Inventory()) == {'fig': row(4, 0)}),
    ('4: available is on hand minus reserved', lambda s: stocked(s).available('apple') == 6),
    ('4: available of unknown sku raises KeyError', lambda s: raises(KeyError, s.Inventory().available, 'apple')),
    ('5: reserve unknown sku raises KeyError', lambda s: unchanged_after_error(s, KeyError, lambda i: i.reserve('o1', 'kiwi', 1))),
    ('5: reserve beyond on hand raises and changes nothing', lambda s: unchanged_after_error(s, ValueError, lambda i: i.reserve('o2', 'pear', 3))),
    ('5: reserve counts other reservations', reserve_counts_existing),
    ('5: reserve exactly the available units', reserve_all_available),
    ('5: reserving again adds', reserve_adds),
    ('6: reservation is 0 when none held', lambda s: stocked(s).reservation('o9', 'apple') == 0),
    ('6: reservations are per sku', reservations_per_sku),
    ('7: release returns units and frees them', release_returns_and_frees),
    ('7: release without reservation raises KeyError', lambda s: unchanged_after_error(s, KeyError, lambda i: i.release('o2', 'apple'))),
    ('7: second release raises KeyError', release_twice),
    ('8: ship lowers reservation and on hand', ship_lowers_both),
    ('8: ship without reservation raises KeyError', lambda s: unchanged_after_error(s, KeyError, lambda i: i.ship('o1', 'pear', 1))),
    ('8: ship beyond reservation raises and changes nothing', lambda s: unchanged_after_error(s, ValueError, lambda i: i.ship('o1', 'apple', 5))),
    ('8: reservation shipped to zero is removed', ship_to_zero_removes),
    ('9: snapshot rows', lambda s: stocked(s).snapshot() == {'apple': row(10, 4), 'pear': row(2, 0)}),
    ('9: snapshot keys sorted', snapshot_sorted),
    ('9: changing a snapshot row leaves inventory unchanged', snapshot_inner_copy),
    ('9: changing the snapshot dict leaves inventory unchanged', snapshot_outer_copy),
]

if __name__ == '__main__':
    main(CHECKS)
