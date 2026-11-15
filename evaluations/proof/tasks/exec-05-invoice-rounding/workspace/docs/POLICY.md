# How we compute invoices and credit notes

Finance owns this policy. Billing code follows it. Where the two disagree, the code is wrong.

## Amounts and lines

Every amount on an invoice or a credit note is a whole number of cents. Unit prices are net of tax.

A line has a quantity, a unit price, a discount percentage and a tax code. Its gross amount is the quantity times the unit price. Its discount is the discount percentage of the gross amount, rounded to the cent on that line. Its net amount is the gross amount less that discount.

*Example.* Two atlases at 12.00 with a 10 % discount: gross 24.00, discount 2.40, net 21.60.

The discount percentage runs from 0 to 100. At 100 the net amount is 0.00, and the line stays on the invoice.

A quantity can be negative, for goods we take back and settle on the same invoice. The gross amount, the discount and the net amount of such a line are then negative, by the same rules as for any other line.

*Example.* Two crates taken back at 1.50 each, no discount: gross -3.00, discount 0.00, net -3.00.

## Tax

Each tax code stands for a tax rate. `billing/rates.py` lists them. Several codes can carry the same rate.

We charge tax per rate, not per line. For each rate, add up the net amounts of all the lines at that rate, whatever their tax codes, take the rate's percentage of that sum, and round once.

*Example.* Two lines at 19 %, each with a net amount of 10.02. The sum is 20.04 and 19 % of it is 3.8076, so the tax is 3.81. Taxing each line would give 1.90 twice, which is 3.80, and that is not what we charge.

The tax breakdown of an invoice has one entry for each rate found on its lines. The entry gives the sum of the net amounts at that rate and the tax on that sum. Entries run from the highest rate to the lowest. A rate stays in the breakdown when its tax is 0.00. The 0 % rate is listed, and so is a rate whose net amounts add up to 0.00.

## Totals

The net total is the sum of the net amounts of the lines. The tax total is the sum of the taxes in the breakdown. The invoice total is the net total plus the tax total.

## Rounding

We round to the nearest cent. An amount that lies exactly halfway between two cents is rounded away from zero: 2.565 becomes 2.57, and -2.565 becomes -2.57. Negative amounts follow the same rule as positive ones, which is what lets a credit note mirror its invoice.

The arithmetic is exact. A percentage is a decimal number: 8.75 % is 875/10000, and 17.5 % is 175/1000. Binary floating point must never decide which way an amount rounds. An amount that lies exactly halfway between two cents in decimal arithmetic is rounded away from zero, whatever a float computation makes of it.

## Credit notes

A credit note has the parts of an invoice: lines, a tax breakdown and totals.

A full credit note cancels an invoice. It is the exact negative of that invoice, cent for cent and in every figure: the gross amount, the discount and the net amount of every line, the net amount and the tax of every entry in the breakdown, and the three totals. Lines and breakdown entries keep the order they have on the invoice.

A partial credit note gives back part of the quantity of some lines. We compute it as if the credited quantities were an invoice of their own. Take the lines being credited, in the order they have on the invoice, each with its credited quantity in place of its invoiced quantity. Compute the invoice for those lines by the rules above. The credit note is the exact negative of that invoice. A line that is not credited is not on the credit note, and a rate found only on such lines is not in its breakdown.

*Example.* An invoice has three mugs at 4.50, taxed at 19 %. To credit one mug, compute an invoice for one mug: net 4.50, and tax of 0.855, which rounds to 0.86. The credit note shows a net total of -4.50, a tax total of -0.86 and a total of -5.36.
