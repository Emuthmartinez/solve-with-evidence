class CartError(Exception):
    """A line that cannot be sold. `sku` is the SKU as the caller wrote it."""

    def __init__(self, sku):
        super().__init__(sku)
        self.sku = sku


class UnknownProduct(CartError):
    pass


class Discontinued(CartError):
    pass
