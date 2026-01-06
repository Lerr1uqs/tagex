"""
核心模块

提供标签提取的核心功能
"""

from tagex.core.schemas import (
    TaggedCode,
    ExtractorConfig,
    ExtractionResult,
    NodeCollectionResult
)
from tagex.core.extractor import TagExtractor, TagCollector
from tagex.core.formatter import OutputFormatter

__all__ = [
    "TaggedCode",
    "ExtractorConfig",
    "ExtractionResult",
    "NodeCollectionResult",
    "TagExtractor",
    "TagCollector",
    "OutputFormatter"
]