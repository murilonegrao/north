import pytest

from north.domain.countries.us.rent import bedrooms_for


@pytest.mark.parametrize(
    ("dependents", "bedrooms"),
    [(0, 1), (1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (7, 4), (12, 4)],
)
def test_bedrooms_for(dependents: int, bedrooms: int) -> None:
    assert bedrooms_for(dependents) == bedrooms


def test_family_of_five_needs_three_bedrooms() -> None:
    # Record 0002, R6: "A family of 5 -> 3 bedrooms".
    assert bedrooms_for(4) == 3


def test_negative_dependents_rejected() -> None:
    with pytest.raises(ValueError):
        bedrooms_for(-1)
