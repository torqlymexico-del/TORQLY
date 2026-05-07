from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")


def to_money(value) -> Decimal:
    if isinstance(value, Decimal):
        amount = value
    else:
        amount = Decimal(str(value or 0))
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

