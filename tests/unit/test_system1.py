import pytest

from support_dispatcher.domain.models import TicketCategory
from support_dispatcher.system1.engine import LayaClassifierEngine


@pytest.mark.asyncio
async def test_system1_engine_classification():
    engine = LayaClassifierEngine(min_confidence=0.85)
    await engine.initialize()
    assert engine.is_ready is True

    # 1. SED Ticket
    pred_sed = await engine.classify(
        "Не удается зарегистрировать входящее служебное письмо в СЭД канцелярии."
    )
    assert pred_sed.category == TicketCategory.SED
    assert pred_sed.confidence >= 0.85
    assert pred_sed.abstention == "passed"

    # 2. DKA Ticket (priority check: bug in DKA -> DKA)
    pred_dka = await engine.classify(
        "Сбой и ошибка при формировании приказа на отпуск сотрудника в кадрах."
    )
    assert pred_dka.category == TicketCategory.DKA
    assert pred_dka.confidence >= 0.85

    # 3. Bug without domain context
    pred_bug = await engine.classify("Сервер возвращает ошибку 500 и traceback, все зависло.")
    assert pred_bug.category == TicketCategory.TECHNICAL_BUG

    # 4. Low-confidence ambiguous ticket
    pred_ambiguous = await engine.classify("Привет, как дела?")
    assert pred_ambiguous.abstention == "abstained"
