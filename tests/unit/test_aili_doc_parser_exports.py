from __future__ import annotations

import importlib


def test_utils_aili_doc_parser_exports_docparser() -> None:
    m = importlib.import_module("src.utils.aili_doc_parser")
    assert hasattr(m, "DocParser")


def test_src_aili_doc_parser_exports_docparser() -> None:
    m = importlib.import_module("src.aili_doc_parser")
    assert hasattr(m, "DocParser")
