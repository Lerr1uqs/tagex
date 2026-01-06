"""
核心提取器模块

本模块提供标签提取的核心功能：
- TagCollector: 使用 libcst 收集包含特定标签的函数和类
- TagExtractor: 标签提取框架主类
"""

from pathlib import Path
from typing import List, Optional
import libcst as cst

from tagex.core.schemas import (
    ExtractorConfig,
    ExtractionResult,
    NodeCollectionResult,
    TaggedCode
)


class TagCollector(cst.CSTVisitor):
    """收集包含特定标签的函数和类"""
    
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)  # type: ignore[attr-defined]
    
    def __init__(self, tag: str, include_functions: bool = True, include_classes: bool = True):
        super().__init__()
        self.tag: str = tag
        self.include_functions: bool = include_functions
        self.include_classes: bool = include_classes
        self.results: List[NodeCollectionResult] = []
        
    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if self.include_functions:
            self._check_node(node, "function")
        return None
    
    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        if self.include_classes:
            self._check_node(node, "class")
        return None
    
    def _check_node(self, node: cst.CSTNode, node_type: str) -> None:
        """检查节点是否包含目标标签"""
        code = cst.Module([node]).code  # type: ignore[list-item]
        
        if self.tag not in code:
            return
        
        if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
            name = node.name.value
        else:
            return
        
        try:
            position = self.get_metadata(cst.metadata.PositionProvider, node)  # type: ignore[attr-defined]
            line_number = position.start.line
        except KeyError:
            line_number = 1
        
        self.results.append(NodeCollectionResult(
            name=name,
            line_number=line_number,
            code=code,
            node_type=node_type
        ))


class TagExtractor:
    """标签提取框架"""
    
    def __init__(self, config: ExtractorConfig):
        """
        初始化提取器
        
        Args:
            config: 提取器配置
        """
        self.config: ExtractorConfig = config
        self._processed_files: int = 0
        self._skipped_files: List[str] = []
        self._results: List[TaggedCode] = []
    
    def extract(self) -> ExtractionResult:
        """提取所有包含标签的代码"""
        py_files = self._get_python_files()
        
        if not py_files:
            return ExtractionResult(
                config=self.config,
                results=self._results,
                processed_files=self._processed_files,
                skipped_files=self._skipped_files
            )
        
        for file_path in py_files:
            self._process_file(file_path)
        
        return ExtractionResult(
            config=self.config,
            results=self._results,
            processed_files=self._processed_files,
            skipped_files=self._skipped_files
        )
    
    def _get_python_files(self) -> List[Path]:
        """获取要处理的 Python 文件列表"""
        if self.config.is_single_file:
            return [self.config.target_path]
        else:
            return sorted(self.config.target_path.rglob(self.config.file_pattern))
    
    def _process_file(self, file_path: Path) -> None:
        """处理单个 Python 文件"""
        source_code = file_path.read_text(encoding='utf-8')
        
        if self.config.tag not in source_code:
            self._processed_files += 1
            return
        
        module = cst.parse_module(source_code)
        
        wrapper = cst.metadata.MetadataWrapper(module)  # type: ignore[attr-defined]
        collector = TagCollector(
            tag=self.config.tag,
            include_functions=self.config.include_functions,
            include_classes=self.config.include_classes
        )
        wrapper.visit(collector)
        
        try:
            relative_path = file_path.relative_to(self.config.base_path)
        except ValueError:
            relative_path = file_path
        
        for result in collector.results:
            self._results.append(TaggedCode(
                file_path=relative_path,
                name=result.name,
                line_number=result.line_number,
                code=result.code,
                node_type=result.node_type
            ))
        
        self._processed_files += 1


# ============================================
# 单元测试
# ============================================

import pytest
from pathlib import Path
import tempfile
import os
from typing import no_type_check


@no_type_check
class TestTagCollector:
    """测试 TagCollector 类"""
    
    def test_collect_function_with_tag(self) -> None:
        """测试收集包含标签的函数"""
        code = '''
def test_func():
    # TODO: implement this
    pass
'''
        module = cst.parse_module(code)
        wrapper = cst.metadata.MetadataWrapper(module)  # type: ignore[attr-defined]
        collector = TagCollector(tag="TODO:", include_functions=True, include_classes=False)
        wrapper.visit(collector)
        
        assert len(collector.results) == 1
        assert collector.results[0].name == "test_func"
        assert collector.results[0].node_type == "function"
    
    def test_collect_class_with_tag(self) -> None:
        """测试收集包含标签的类"""
        code = '''
class TestClass:
    # TODO: implement this
    pass
'''
        module = cst.parse_module(code)
        wrapper = cst.metadata.MetadataWrapper(module)  # type: ignore[attr-defined]
        collector = TagCollector(tag="TODO:", include_functions=False, include_classes=True)
        wrapper.visit(collector)
        
        assert len(collector.results) == 1
        assert collector.results[0].name == "TestClass"
        assert collector.results[0].node_type == "class"
    
    def test_collect_without_tag(self) -> None:
        """测试不包含标签的代码"""
        code = '''
def test_func():
    pass
'''
        module = cst.parse_module(code)
        wrapper = cst.metadata.MetadataWrapper(module)  # type: ignore[attr-defined]
        collector = TagCollector(tag="TODO:", include_functions=True, include_classes=False)
        wrapper.visit(collector)
        
        assert len(collector.results) == 0
    
    def test_collect_both_functions_and_classes(self) -> None:
        """测试同时收集函数和类"""
        code = '''
def test_func():
    # TODO: implement this
    pass

class TestClass:
    # TODO: implement this
    pass
'''
        module = cst.parse_module(code)
        wrapper = cst.metadata.MetadataWrapper(module)  # type: ignore[attr-defined]
        collector = TagCollector(tag="TODO:", include_functions=True, include_classes=True)
        wrapper.visit(collector)
        
        assert len(collector.results) == 2


@no_type_check
class TestTagExtractor:
    """测试 TagExtractor 类"""
    
    def test_extract_from_single_file(self) -> None:
        """测试从单个文件提取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    # TODO: implement this
    pass
''')
            
            config = ExtractorConfig(
                tag="TODO:",
                target_path=test_file,
                include_functions=True,
                include_classes=True
            )
            
            extractor = TagExtractor(config=config)
            result = extractor.extract()
            
            assert result.total_matches == 1
            assert result.processed_files == 1
            assert result.results[0].name == "test_func"
    
    def test_extract_from_directory(self) -> None:
        """测试从目录提取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file1 = Path(tmpdir) / "test1.py"
            test_file1.write_text('''
def func1():
    # TODO: implement this
    pass
''')
            
            test_file2 = Path(tmpdir) / "test2.py"
            test_file2.write_text('''
def func2():
    # TODO: implement this
    pass
''')
            
            config = ExtractorConfig(
                tag="TODO:",
                target_path=Path(tmpdir),
                include_functions=True,
                include_classes=True
            )
            
            extractor = TagExtractor(config=config)
            result = extractor.extract()
            
            assert result.total_matches == 2
            assert result.processed_files == 2
    
    def test_extract_no_matches(self) -> None:
        """测试没有匹配项的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    pass
''')
            
            config = ExtractorConfig(
                tag="TODO:",
                target_path=test_file,
                include_functions=True,
                include_classes=True
            )
            
            extractor = TagExtractor(config=config)
            result = extractor.extract()
            
            assert result.total_matches == 0
            assert result.processed_files == 1
    
    def test_extract_only_functions(self) -> None:
        """测试只提取函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    # TODO: implement this
    pass

class TestClass:
    # TODO: implement this
    pass
''')
            
            config = ExtractorConfig(
                tag="TODO:",
                target_path=test_file,
                include_functions=True,
                include_classes=False
            )
            
            extractor = TagExtractor(config=config)
            result = extractor.extract()
            
            assert result.total_matches == 1
            assert result.results[0].node_type == "function"
    
    def test_extract_only_classes(self) -> None:
        """测试只提取类"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    # TODO: implement this
    pass

class TestClass:
    # TODO: implement this
    pass
''')
            
            config = ExtractorConfig(
                tag="TODO:",
                target_path=test_file,
                include_functions=False,
                include_classes=True
            )
            
            extractor = TagExtractor(config=config)
            result = extractor.extract()
            
            assert result.total_matches == 1
            assert result.results[0].node_type == "class"
    
    def test_relative_path_calculation(self) -> None:
        """测试相对路径计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            test_file = subdir / "test.py"
            test_file.write_text('''
def test_func():
    # TODO: implement this
    pass
''')
            
            config = ExtractorConfig(
                tag="TODO:",
                target_path=Path(tmpdir),
                include_functions=True,
                include_classes=True
            )
            
            extractor = TagExtractor(config=config)
            result = extractor.extract()
            
            assert result.total_matches == 1
            assert result.results[0].file_path == Path("subdir/test.py")