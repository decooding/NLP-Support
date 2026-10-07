"""Dataset processor and converter for Smart Support Dispatcher.

Parses raw tickets from Service Desk, cleans noise and 'Отказ' entries,
maps domain categories, and splits into train and eval sets.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

from support_dispatcher.domain.models import TicketCategory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def map_category(item: dict[str, Any]) -> TicketCategory:
    """Maps Service Desk ticket attributes to project taxonomy."""
    ztype = (item.get("o_ztype") or "").strip().lower()
    req_type = (item.get("o_request_type") or "").strip().lower()
    text = (item.get("o_description") or "").strip().lower()

    # 1. Feature request
    if "доработк" in req_type or "разработк" in req_type or "модификаци" in req_type:
        return TicketCategory.FEATURE_REQUEST

    # 2. Technical Bug
    if "техническая ошибка" in req_type or "системн" in req_type:
        return TicketCategory.TECHNICAL_BUG

    # 3. Access & General Inquiry
    if "доступ" in req_type or "консультац" in req_type:
        return TicketCategory.GENERAL_INQUIRY

    # 4. Domain Priority Rules (СЭД vs ДКА)
    sed_markers = [
        "сэд", "входящ", "исходящ", "служебн", "делопроизвод",
        "письм", "канцеляр", "документооборот", "согласован",
    ]
    dka_markers = [
        "отпуск", "приказ", "командировк", "кадр", "штатн", "увольнен",
        "больничн", "табель", "личн", "прием", "обходной", "стаж",
    ]

    has_sed = any(m in text for m in sed_markers)
    has_dka = any(m in text for m in dka_markers)

    if has_sed and not has_dka:
        return TicketCategory.SED
    if has_dka:
        return TicketCategory.DKA

    # 5. Default by ztype
    if "сэд" in ztype:
        return TicketCategory.SED
    if "другое" in ztype:
        return TicketCategory.DKA

    return TicketCategory.OTHER


def process_dataset(
    raw_path: Path,
    eval_output_path: Path,
    train_output_path: Path,
    eval_size: int = 1200,
    random_seed: int = 42,
) -> None:
    """Cleans, categorizes, and splits raw dataset into train and eval jsonl files."""
    logger.info("Loading raw dataset from %s...", raw_path)
    with raw_path.open("r", encoding="utf-8") as f:
        raw_dict: dict[str, dict[str, Any]] = json.load(f)

    logger.info("Total entries loaded: %d", len(raw_dict))

    cleaned_items: list[dict[str, Any]] = []
    skipped_refused = 0
    skipped_empty = 0

    for ticket_id, item in raw_dict.items():
        state = (item.get("o_state") or "").strip()
        text = (item.get("o_description") or "").strip()

        # Clean noise: empty texts or non-informative rejected tickets
        if not text:
            skipped_empty += 1
            continue

        if state == "Отказ" and ("удалите" in text.lower() or "неактуальн" in text.lower() or "ошибочн" in text.lower()):
            skipped_refused += 1
            continue

        category = map_category(item)

        cleaned_items.append({
            "ticket_id": str(ticket_id),
            "text": text,
            "category": category.value,
            "reply": item.get("o_reply") or "",
            "raw_ztype": item.get("o_ztype"),
            "raw_request_type": item.get("o_request_type"),
            "raw_state": state,
        })

    logger.info(
        "Cleaned items: %d (Skipped empty: %d, Skipped refused/deleted: %d)",
        len(cleaned_items),
        skipped_empty,
        skipped_refused,
    )

    # Stratified or randomized train / eval split
    random.seed(random_seed)
    random.shuffle(cleaned_items)

    eval_items = cleaned_items[:eval_size]
    train_items = cleaned_items[eval_size:]

    eval_output_path.parent.mkdir(parents=True, exist_ok=True)
    train_output_path.parent.mkdir(parents=True, exist_ok=True)

    with eval_output_path.open("w", encoding="utf-8") as f:
        for item in eval_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with train_output_path.open("w", encoding="utf-8") as f:
        for item in train_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info("Saved eval dataset: %s (%d records)", eval_output_path, len(eval_items))
    logger.info("Saved train dataset: %s (%d records)", train_output_path, len(train_items))


if __name__ == "__main__":
    raw_file = Path("data/raw/ticket_dataest.json")
    eval_file = Path("data/eval/test_dataset.jsonl")
    train_file = Path("data/processed/train.jsonl")
    process_dataset(raw_file, eval_file, train_file)
