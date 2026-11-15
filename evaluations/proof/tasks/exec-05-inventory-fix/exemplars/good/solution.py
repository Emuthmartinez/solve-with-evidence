"""Stock ledger. SPEC.md states the rules."""


class Inventory:
    def __init__(self):
        self._stock = {}
        self._orders = {}

    def _check_qty(self, qty):
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError(f'quantity must be a positive int, got {qty!r}')

    def _row(self, sku):
        if sku not in self._stock:
            raise KeyError(sku)
        return self._stock[sku]

    def _held(self, order_id, sku):
        key = (order_id, sku)
        if key not in self._orders:
            raise KeyError(f'order {order_id!r} holds no {sku!r}')
        return key

    def restock(self, sku, qty):
        self._check_qty(qty)
        row = self._stock.setdefault(sku, {'on_hand': 0, 'reserved': 0})
        row['on_hand'] += qty

    def available(self, sku):
        row = self._row(sku)
        return row['on_hand'] - row['reserved']

    def reserve(self, order_id, sku, qty):
        self._check_qty(qty)
        row = self._row(sku)
        if qty > row['on_hand'] - row['reserved']:
            raise ValueError(f'only {row["on_hand"] - row["reserved"]} of {sku!r} available')
        row['reserved'] += qty
        key = (order_id, sku)
        self._orders[key] = self._orders.get(key, 0) + qty

    def reservation(self, order_id, sku):
        return self._orders.get((order_id, sku), 0)

    def release(self, order_id, sku):
        key = self._held(order_id, sku)
        qty = self._orders.pop(key)
        self._stock[sku]['reserved'] -= qty
        return qty

    def ship(self, order_id, sku, qty):
        self._check_qty(qty)
        key = self._held(order_id, sku)
        if qty > self._orders[key]:
            raise ValueError(f'order {order_id!r} holds only {self._orders[key]} of {sku!r}')
        row = self._stock[sku]
        row['on_hand'] -= qty
        row['reserved'] -= qty
        self._orders[key] -= qty
        if self._orders[key] == 0:
            del self._orders[key]

    def snapshot(self):
        result = {}
        for sku in sorted(self._stock):
            row = self._stock[sku]
            result[sku] = {**row, 'available': row['on_hand'] - row['reserved']}
        return result
