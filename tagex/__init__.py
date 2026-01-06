"""
TagEx - Tag Extractor

一个用于从 Python 代码中提取特定标签（如 TODO、FIXME、AGENT-TODO 等）的工具
"""

__version__ = "1.0.0"
__author__ = "TagEx Team"

from tagex.core import (
    TaggedCode,
    ExtractorConfig,
    ExtractionResult,
    TagExtractor,
    OutputFormatter
)

__all__ = [
    "__version__",
    "TaggedCode",
    "ExtractorConfig",
    "ExtractionResult",
    "TagExtractor",
    "OutputFormatter"
]