import pytest

from support_dispatcher.core.config import ValidationError
from support_dispatcher.domain.models import Ticket
from support_dispatcher.preprocessing.cleaner import Preprocessor


def test_preprocessor_validation():
    p = Preprocessor(cache_ttl_seconds=60)

    # Empty text
    with pytest.raises(ValidationError):
        p.validate_and_clean(Ticket(ticket_id="T1", text="   "))

    # Empty ID
    with pytest.raises(ValidationError):
        p.validate_and_clean(Ticket(ticket_id="  ", text="Valid text"))

    # Zero-width / control characters removal
    ticket = Ticket(ticket_id="T2", text="Текст\x00\x1f с пробелами   и символами")
    cleaned = p.validate_and_clean(ticket)
    assert cleaned == "Текст с пробелами и символами"

    # Deduplication
    assert p.is_duplicate("T2") is False
    assert p.is_duplicate("T2") is True
