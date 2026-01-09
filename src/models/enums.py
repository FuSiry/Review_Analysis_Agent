from __future__ import annotations

from enum import StrEnum


class Mode(StrEnum):
    chat = "chat"
    prd_review = "prd_review"
    trd_review = "trd_review"
    tc_review = "tc_review"

