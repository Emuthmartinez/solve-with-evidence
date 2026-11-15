"""The records the importer hands to the ledger."""
from collections import namedtuple

# booking_date is a datetime.date. value_date is a datetime.date, or None when the bank left it empty.
# status is 'booked' or 'pending'. amount_minor is an int in the currency's minor unit (cents for EUR,
# fils for KWD, yen for JPY), negative for a debit. currency is the ISO code, memo the text as the bank wrote it.
Transaction = namedtuple('Transaction', 'booking_date value_date reference status amount_minor currency memo')


class FormatError(ValueError):
    """The file does not follow the bank's export format."""
