"""
数据模型定义模块

本模块定义了所有使用 Pydantic 的数据模型，包括：
- TaggedCode: 存储带标签的代码信息
- ExtractorConfig: 提取器配置
- ExtractionResult: 提取结果
- NodeCollectionResult: 节点收集结果
"""

from pathlib import Path
from typing import List, Dict, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TaggedCode(BaseModel):
    """存储带标签的代码信息"""
    model_config = ConfigDict(frozen=True)
    
    file_path: Path = Field(..., description="文件相对路径")
    name: str = Field(..., description="函数或类名")
    line_number: int = Field(..., ge=1, description="起始行号")
    code: str = Field(..., description="源代码")
    node_type: str = Field(..., description="节点类型: function 或 class")
    
    @field_validator('node_type')
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        if v not in ['function', 'class']:
            raise ValueError(f"node_type must be 'function' or 'class', got '{v}'")
        return v


class ExtractorConfig(BaseModel):
    """提取器配置"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    tag: str = Field(..., min_length=1, description="要搜索的标签")
    target_path: Path = Field(..., description="要搜索的文件或目录")
    include_functions: bool = Field(default=True, description="是否包含函数")
    include_classes: bool = Field(default=True, description="是否包含类")
    file_pattern: str = Field(default="*.py", description="文件匹配模式（仅目录时生效）")
    
    @field_validator('target_path')
    @classmethod
    def validate_target_path(cls, v: Union[str, Path]) -> Path:
        path = Path(v) if isinstance(v, str) else v
        path = path.resolve()
        
        if not path.exists():
            raise ValueError(f"路径不存在: {path}")
        
        if path.is_file() and path.suffix != '.py':
            raise ValueError(f"不是 Python 文件: {path}")
        
        return path
    
    @property
    def is_single_file(self) -> bool:
        """判断是否为单文件模式"""
        return self.target_path.is_file()
    
    @property
    def base_path(self) -> Path:
        """获取基准路径（用于计算相对路径）"""
        if self.is_single_file:
            return self.target_path.parent
        else:
            return self.target_path


class ExtractionResult(BaseModel):
    """提取结果"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    config: ExtractorConfig
    results: List[TaggedCode] = Field(default_factory=list)
    processed_files: int = Field(default=0, ge=0)
    skipped_files: List[str] = Field(default_factory=list)
    
    @property
    def total_matches(self) -> int:
        return len(self.results)
    
    def group_by_file(self) -> Dict[Path, List[TaggedCode]]:
        """按文件路径分组"""
        grouped: Dict[Path, List[TaggedCode]] = {}
        for item in self.results:
            if item.file_path not in grouped:
                grouped[item.file_path] = []
            grouped[item.file_path].append(item)
        return grouped


class NodeCollectionResult(BaseModel):
    """节点收集结果"""
    model_config = ConfigDict(frozen=True)
    
    name: str = Field(..., description="节点名称")
    line_number: int = Field(..., ge=1, description="行号")
    code: str = Field(..., description="源代码")
    node_type: str = Field(..., description="节点类型")


# ============================================
# 单元测试
# ============================================

import pytest
from typing import no_type_check


@no_type_check
class TestTaggedCode:
    """测试 TaggedCode 模型"""
    
    def test_create_tagged_code(self) -> None:
        """测试创建 TaggedCode 实例"""
        tagged_code = TaggedCode(
            file_path=Path("test.py"),
            name="test_func",
            line_number=10,
            code="def test_func(): pass",
            node_type="function"
        )
        assert tagged_code.name == "test_func"
        assert tagged_code.line_number == 10
        assert tagged_code.node_type == "function"
    
    def test_invalid_node_type(self) -> None:
        """测试无效的节点类型"""
        with pytest.raises(ValueError, match="node_type must be 'function' or 'class'"):
            TaggedCode(
                file_path=Path("test.py"),
                name="test",
                line_number=10,
                code="test",
                node_type="invalid"
            )
    
    def test_line_number_validation(self) -> None:
        """测试行号验证"""
        with pytest.raises(ValueError):
            TaggedCode(
                file_path=Path("test.py"),
                name="test",
                line_number=0,
                code="test",
                node_type="function"
            )


@no_type_check
class TestExtractorConfig:
    """测试 ExtractorConfig 模型"""
    
    def test_create_config(self) -> None:
        """测试创建配置"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__).parent,
            include_functions=True,
            include_classes=True
        )
        assert config.tag == "TODO:"
        assert config.include_functions is True
        assert config.include_classes is True
    
    def test_invalid_path(self) -> None:
        """测试无效路径"""
        with pytest.raises(ValueError, match="路径不存在"):
            ExtractorConfig(
                tag="TODO:",
                target_path=Path("/nonexistent/path")
            )
    
    def test_empty_tag(self) -> None:
        """测试空标签"""
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            ExtractorConfig(
                tag="",
                target_path=Path(__file__).parent
            )
    
    def test_is_single_file(self) -> None:
        """测试单文件模式判断"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__)
        )
        assert config.is_single_file is True
    
    def test_base_path_single_file(self) -> None:
        """测试单文件模式的基准路径"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__)
        )
        assert config.base_path == Path(__file__).parent


@no_type_check
class TestExtractionResult:
    """测试 ExtractionResult 模型"""
    
    def test_create_result(self) -> None:
        """测试创建提取结果"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__).parent
        )
        result = ExtractionResult(
            config=config,
            results=[],
            processed_files=0,
            skipped_files=[]
        )
        assert result.total_matches == 0
        assert result.processed_files == 0
    
    def test_group_by_file(self) -> None:
        """测试按文件分组"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__).parent
        )
        
        tagged_code1 = TaggedCode(
            file_path=Path("test1.py"),
            name="func1",
            line_number=10,
            code="def func1(): pass",
            node_type="function"
        )
        tagged_code2 = TaggedCode(
            file_path=Path("test1.py"),
            name="func2",
            line_number=20,
            code="def func2(): pass",
            node_type="function"
        )
        tagged_code3 = TaggedCode(
            file_path=Path("test2.py"),
            name="func3",
            line_number=30,
            code="def func3(): pass",
            node_type="function"
        )
        
        result = ExtractionResult(
            config=config,
            results=[tagged_code1, tagged_code2, tagged_code3],
            processed_files=2,
            skipped_files=[]
        )
        
        grouped = result.group_by_file()
        assert len(grouped) == 2
        assert Path("test1.py") in grouped
        assert Path("test2.py") in grouped
        assert len(grouped[Path("test1.py")]) == 2
        assert len(grouped[Path("test2.py")]) == 1


@no_type_check
class TestNodeCollectionResult:
    """测试 NodeCollectionResult 模型"""
    
    def test_create_result(self) -> None:
        """测试创建节点收集结果"""
        result = NodeCollectionResult(
            name="test_func",
            line_number=10,
            code="def test_func(): pass",
            node_type="function"
        )
        assert result.name == "test_func"
        assert result.line_number == 10
        assert result.node_type == "function"