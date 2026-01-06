"""
CLI 模块 - 命令行接口

提供命令行接口和便捷函数
"""

from pathlib import Path
from typing import Optional, Union
import typer
from rich.console import Console
from rich.panel import Panel
from rich.traceback import Traceback

from tagex.core import ExtractorConfig, TagExtractor, OutputFormatter, ExtractionResult
from tagex.logger import logger

console = Console()

app = typer.Typer(
    name="tagex",
    help="🔍 提取代码中的特定标签（TODO、FIXME、AGENT-TODO 等）",
    add_completion=False
)


@app.command()
def extract(
    path: Path = typer.Argument(
        ...,
        help="要搜索的文件或目录路径",
        exists=True,
        resolve_path=True
    ),
    tag: str = typer.Option(
        "TODO:",
        "--tag", "-t",
        help="要搜索的标签"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="输出文件路径（可选）"
    ),
    format: str = typer.Option(
        "markdown",
        "--format", "-f",
        help="输出格式: markdown 或 plain"
    ),
    no_functions: bool = typer.Option(
        False,
        "--no-functions",
        help="不包含函数"
    ),
    no_classes: bool = typer.Option(
        False,
        "--no-classes",
        help="不包含类"
    ),
    table_view: bool = typer.Option(
        False,
        "--table", "-T",
        help="以表格形式显示结果"
    ),
    no_code: bool = typer.Option(
        False,
        "--no-code",
        help="不显示代码内容"
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="静默模式，不显示进度"
    )
) -> None:
    """
    提取代码中的特定标签
    
    示例:
    
        # 搜索单个文件
        tagex extract myfile.py --tag "TODO:"
        
        # 搜索目录
        tagex extract ./src --tag "AGENT-TODO:"
        
        # 搜索并保存
        tagex extract ./src --tag "TODO:" --output todos.md
        
        # 只搜索函数
        tagex extract ./src --tag "FIXME:" --no-classes
        
        # 表格视图
        tagex extract ./src --tag "TODO:" --table
    """
    config = ExtractorConfig(
        tag=tag,
        target_path=path,
        include_functions=not no_functions,
        include_classes=not no_classes
    )
    
    if not quiet:
        mode = "单文件" if config.is_single_file else "目录递归"
        console.print(Panel(
            f"[cyan]标签:[/cyan] [bold]{tag}[/bold]\n"
            f"[cyan]模式:[/cyan] {mode}\n"
            f"[cyan]路径:[/cyan] {path}\n"
            f"[cyan]包含:[/cyan] "
            f"{'函数 ' if config.include_functions else ''}"
            f"{'类 ' if config.include_classes else ''}",
            title="🔍 搜索配置",
            border_style="cyan"
        ))
    
    extractor = TagExtractor(config=config)
    result = extractor.extract()
    
    if not quiet:
        OutputFormatter.print_summary(result)
    
    if table_view:
        OutputFormatter.print_table(result)
    else:
        OutputFormatter.print_results(result, show_code=not no_code)
    
    if output:
        OutputFormatter.save_to_file(result, output, format=format)


@app.command()
def version() -> None:
    """显示版本信息"""
    console.print(Panel(
        "[bold cyan]Tag Extractor[/bold cyan]\n"
        "版本: 1.0.0\n"
        "支持单文件和目录搜索\n"
        "基于 Pydantic V2 + libcst + Rich",
        title="📦 版本信息",
        border_style="cyan"
    ))


def extract_tags(
    path: Union[str, Path],
    tag: str = "TODO:",
    include_functions: bool = True,
    include_classes: bool = True,
    output_file: Optional[Union[str, Path]] = None,
    output_format: str = "markdown",
    show_progress: bool = True,
    show_code: bool = True
) -> ExtractionResult:
    """
    便捷函数：提取代码中的特定标签
    
    Args:
        path: 要搜索的文件或目录路径
        tag: 要搜索的标签
        include_functions: 是否包含函数
        include_classes: 是否包含类
        output_file: 输出文件路径（可选）
        output_format: 输出格式 (markdown 或 plain)
        show_progress: 是否显示进度条
        show_code: 是否显示代码内容
    
    Returns:
        提取结果
    """
    config = ExtractorConfig(
        tag=tag,
        target_path=Path(path),
        include_functions=include_functions,
        include_classes=include_classes
    )
    
    extractor = TagExtractor(config=config)
    result = extractor.extract()
    
    OutputFormatter.print_summary(result)
    OutputFormatter.print_results(result, show_code=show_code)
    
    if output_file:
        output_path = Path(output_file)
        OutputFormatter.save_to_file(result, output_path, format=output_format)
    
    return result


def main() -> None:
    """主函数入口"""
    try:
        app()
    except Exception as e:
        t = Traceback.from_exception(type(e), e, e.__traceback__)
        with console.capture() as capture:
            console.print(t)
        if logger:
            logger.info("\n" + capture.get())

if __name__ == "__main__":
    main()

# ============================================
# 单元测试
# ============================================

import pytest
from pathlib import Path
import tempfile
from typing import no_type_check


@no_type_check
class TestCLI:
    """测试 CLI 功能"""
    
    def test_extract_tags_function(self) -> None:
        """测试 extract_tags 便捷函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    # TODO: implement this
    pass
''')
            
            result = extract_tags(
                path=test_file,
                tag="TODO:",
                show_progress=False,
                show_code=False
            )
            
            assert result.total_matches == 1
            assert result.results[0].name == "test_func"
    
    def test_extract_tags_with_output(self) -> None:
        """测试 extract_tags 带输出文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    # TODO: implement this
    pass
''')
            
            output_file = Path(tmpdir) / "output.md"
            
            result = extract_tags(
                path=test_file,
                tag="TODO:",
                output_file=output_file,
                show_progress=False,
                show_code=False
            )
            
            assert result.total_matches == 1
            assert output_file.exists()
            content = output_file.read_text(encoding='utf-8')
            assert "# 代码标签提取报告" in content
    
    def test_extract_tags_directory(self) -> None:
        """测试 extract_tags 处理目录"""
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
            
            result = extract_tags(
                path=tmpdir,
                tag="TODO:",
                show_progress=False,
                show_code=False
            )
            
            assert result.total_matches == 2
    
    def test_extract_tags_no_matches(self) -> None:
        """测试 extract_tags 无匹配项"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def test_func():
    pass
''')
            
            result = extract_tags(
                path=test_file,
                tag="TODO:",
                show_progress=False,
                show_code=False
            )
            
            assert result.total_matches == 0
    
    def test_extract_tags_only_functions(self) -> None:
        """测试 extract_tags 只提取函数"""
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
            
            result = extract_tags(
                path=test_file,
                tag="TODO:",
                include_functions=True,
                include_classes=False,
                show_progress=False,
                show_code=False
            )
            
            assert result.total_matches == 1
            assert result.results[0].node_type == "function"
    
    def test_extract_tags_only_classes(self) -> None:
        """测试 extract_tags 只提取类"""
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
            
            result = extract_tags(
                path=test_file,
                tag="TODO:",
                include_functions=False,
                include_classes=True,
                show_progress=False,
                show_code=False
            )
            
            assert result.total_matches == 1
            assert result.results[0].node_type == "class"