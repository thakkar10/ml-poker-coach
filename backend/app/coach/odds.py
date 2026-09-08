from __future__ import annotations


def pot_odds(amount_to_call: int, pot: int) -> float:
    """Return break-even equity required to call."""
    if amount_to_call <= 0:
        return 0.0
    if pot < 0:
        raise ValueError("pot cannot be negative")
    return amount_to_call / (pot + amount_to_call)


def stack_to_pot_ratio(stack: int, pot: int) -> float:
    if stack < 0 or pot < 0:
        raise ValueError("stack and pot cannot be negative")
    if pot == 0:
        return float("inf")
    return stack / pot
