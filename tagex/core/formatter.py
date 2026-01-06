"""
输出格式化模块

本模块提供多种输出格式的支持：
- Markdown 格式
- 纯文本格式
- 终端表格视图
- 树形视图
"""

from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.tree import Tree
from rich import box

from tagex.core.schemas import ExtractionResult


console = Console()


class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def print_summary(result: ExtractionResult) -> None:
        """打印摘要信息"""
        table = Table(title="提取摘要", box=box.ROUNDED, show_header=False)
        table.add_column("项目", style="cyan", no_wrap=True)
        table.add_column("值", style="magenta")
        
        table.add_row("搜索标签", f"[bold]{result.config.tag}[/bold]")
        
        if result.config.is_single_file:
            table.add_row("搜索模式", "[bold]单文件[/bold]")
            table.add_row("文件路径", str(result.config.target_path))
        else:
            table.add_row("搜索模式", "[bold]目录递归[/bold]")
            table.add_row("搜索目录", str(result.config.target_path))
            table.add_row("处理文件数", str(result.processed_files))
        
        table.add_row("找到匹配项", f"[bold green]{result.total_matches}[/bold green]")
        
        if result.skipped_files:
            table.add_row(
                "跳过文件数",
                f"[yellow]{len(result.skipped_files)}[/yellow]"
            )
        
        console.print(table)
        console.print()
        
        if result.skipped_files:
            console.print("[yellow]⚠ 跳过的文件:[/yellow]")
            for skipped in result.skipped_files[:10]:
                console.print(f"  [dim]• {skipped}[/dim]")
            if len(result.skipped_files) > 10:
                console.print(f"  [dim]... 还有 {len(result.skipped_files) - 10} 个文件[/dim]")
            console.print()
    
    @staticmethod
    def print_results(result: ExtractionResult, show_code: bool = True) -> None:
        """打印结果 - Rich 格式"""
        if result.total_matches == 0:
            console.print(Panel(
                f"[yellow]未找到包含标签 '{result.config.tag}' 的代码[/yellow]",
                title="搜索结果",
                border_style="yellow"
            ))
            return
        
        grouped = result.group_by_file()
        
        tree = Tree(
            f"[bold cyan]找到 {result.total_matches} 个匹配项[/bold cyan]",
            guide_style="dim"
        )
        
        for file_path in sorted(grouped.keys()):
            items = grouped[file_path]
            file_branch = tree.add(
                f"[bold blue]📄 {file_path}[/bold blue] [dim]({len(items)} 个匹配)[/dim]"
            )
            
            for item in sorted(items, key=lambda x: x.line_number):
                icon = "🔧" if item.node_type == "function" else "📦"
                file_branch.add(
                    f"{icon} [green]{item.name}[/green] [dim]({item.node_type}, 第 {item.line_number} 行)[/dim]"
                )
        
        console.print(tree)
        console.print()
        
        if show_code:
            console.print("[bold cyan]详细代码:[/bold cyan]\n")
            
            for file_path in sorted(grouped.keys()):
                items = grouped[file_path]
                
                console.print(Panel(
                    f"[bold]./{file_path}[/bold]",
                    style="blue",
                    expand=False
                ))
                
                for item in sorted(items, key=lambda x: x.line_number):
                    console.print(
                        f"\n[bold yellow]{item.node_type.upper()}[/bold yellow] "
                        f"[bold green]{item.name}[/bold green] "
                        f"[dim](第 {item.line_number} 行)[/dim]"
                    )
                    
                    syntax = Syntax(
                        item.code,
                        "python",
                        theme="monokai",
                        line_numbers=True,
                        start_line=item.line_number,
                        highlight_lines=set()
                    )
                    console.print(syntax)
                    console.print()
    
    @staticmethod
    def print_table(result: ExtractionResult) -> None:
        """以表格形式打印结果"""
        if result.total_matches == 0:
            console.print("[yellow]未找到匹配项[/yellow]")
            return
        
        table = Table(
            title=f"搜索标签: {result.config.tag}",
            box=box.ROUNDED,
            show_lines=True
        )
        
        table.add_column("文件路径", style="cyan", no_wrap=False)
        table.add_column("类型", style="magenta", justify="center")
        table.add_column("名称", style="green")
        table.add_column("行号", style="yellow", justify="right")
        
        for item in sorted(result.results, key=lambda x: (str(x.file_path), x.line_number)):
            icon = "🔧" if item.node_type == "function" else "📦"
            table.add_row(
                f"./{item.file_path}",
                f"{icon} {item.node_type}",
                item.name,
                str(item.line_number)
            )
        
        console.print(table)
    
    @staticmethod
    def save_to_file(result: ExtractionResult, output_path: Path, format: str = "markdown") -> None:
        """保存结果到文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "markdown":
            content = OutputFormatter._format_markdown(result)
        else:
            content = OutputFormatter._format_plain(result)
        
        output_path.write_text(content, encoding='utf-8')
        console.print(f"[green]✓[/green] 结果已保存到: [bold]{output_path}[/bold]")
    
    @staticmethod
    def _format_markdown(result: ExtractionResult) -> str:
        """格式化为 Markdown"""
        lines = [
            f"# 代码标签提取报告",
            f"",
            f"**搜索标签**: `{result.config.tag}`  ",
        ]
        
        if result.config.is_single_file:
            lines.append(f"**搜索模式**: 单文件  ")
            lines.append(f"**文件路径**: `{result.config.target_path}`  ")
        else:
            lines.append(f"**搜索模式**: 目录递归  ")
            lines.append(f"**搜索目录**: `{result.config.target_path}`  ")
            lines.append(f"**处理文件**: {result.processed_files}  ")
        
        lines.append(f"**找到匹配项**: {result.total_matches}  ")
        lines.append("")
        
        if result.skipped_files:
            lines.append(f"**跳过文件**: {len(result.skipped_files)}  ")
            lines.append("")
        
        if result.total_matches == 0:
            lines.append("未找到匹配项。")
            if result.skipped_files:
                lines.append("")
                lines.append("### 跳过的文件")
                for skipped in result.skipped_files:
                    lines.append(f"- {skipped}")
            return "\n".join(lines)
        
        lines.append("---\n")
        
        grouped = result.group_by_file()
        
        for file_path in sorted(grouped.keys()):
            items = grouped[file_path]
            lines.append(f"## 📄 `./{file_path}`\n")
            
            for item in sorted(items, key=lambda x: x.line_number):
                icon = "🔧" if item.node_type == "function" else "📦"
                lines.append(f"### {icon} `{item.name}` ({item.node_type}, 第 {item.line_number} 行)\n")
                lines.append("```python")
                lines.append(item.code)
                lines.append("```\n")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_plain(result: ExtractionResult) -> str:
        """格式化为纯文本"""
        lines = [
            f"搜索标签: {result.config.tag}",
        ]
        
        if result.config.is_single_file:
            lines.append(f"搜索模式: 单文件")
            lines.append(f"文件路径: {result.config.target_path}")
        else:
            lines.append(f"搜索模式: 目录递归")
            lines.append(f"搜索目录: {result.config.target_path}")
            lines.append(f"处理文件: {result.processed_files}")
        
        lines.append(f"找到匹配项: {result.total_matches}")
        lines.append("")
        
        if result.total_matches == 0:
            return "\n".join(lines + ["未找到匹配项。"])
        
        grouped = result.group_by_file()
        
        for file_path in sorted(grouped.keys()):
            items = grouped[file_path]
            lines.append("=" * 60)
            lines.append(f"./{file_path}")
            lines.append("=" * 60)
            
            for item in sorted(items, key=lambda x: x.line_number):
                lines.append(f"\n[{item.node_type.upper()}] {item.name} (第 {item.line_number} 行)")
                lines.append("-" * 60)
                
                code_lines = item.code.split('\n')
                for i, line in enumerate(code_lines):
                    line_num = item.line_number + i
                    lines.append(f"{line_num:4d}    {line}")
                lines.append("")
        
        return "\n".join(lines)


# ============================================
# 单元测试
# ============================================

import pytest
from pathlib import Path
import tempfile
from tagex.core.schemas import ExtractorConfig, TaggedCode, ExtractionResult
from typing import no_type_check


@no_type_check
class TestOutputFormatter:
    """测试 OutputFormatter 类"""
    
    def test_format_markdown(self) -> None:
        """测试 Markdown 格式化"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__).parent
        )
        
        tagged_code = TaggedCode(
            file_path=Path("test.py"),
            name="test_func",
            line_number=10,
            code="def test_func(): pass",
            node_type="function"
        )
        
        result = ExtractionResult(
            config=config,
            results=[tagged_code],
            processed_files=1,
            skipped_files=[]
        )
        
        markdown = OutputFormatter._format_markdown(result)
        
        assert "# 代码标签提取报告" in markdown
        assert "TODO:" in markdown
        assert "test_func" in markdown
        assert "```python" in markdown
    
    def test_format_plain(self) -> None:
        """测试纯文本格式化"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__).parent
        )
        
        tagged_code = TaggedCode(
            file_path=Path("test.py"),
            name="test_func",
            line_number=10,
            code="def test_func(): pass",
            node_type="function"
        )
        
        result = ExtractionResult(
            config=config,
            results=[tagged_code],
            processed_files=1,
            skipped_files=[]
        )
        
        plain = OutputFormatter._format_plain(result)
        
        assert "搜索标签: TODO:" in plain
        assert "test_func" in plain
        assert "第 10 行" in plain
    
    def test_format_empty_result(self) -> None:
        """测试空结果格式化"""
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
        
        markdown = OutputFormatter._format_markdown(result)
        plain = OutputFormatter._format_plain(result)
        
        assert "未找到匹配项" in markdown
        assert "未找到匹配项" in plain
    
    def test_save_to_file(self) -> None:
        """测试保存到文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ExtractorConfig(
                tag="TODO:",
                target_path=Path(__file__).parent
            )
            
            tagged_code = TaggedCode(
                file_path=Path("test.py"),
                name="test_func",
                line_number=10,
                code="def test_func(): pass",
                node_type="function"
            )
            
            result = ExtractionResult(
                config=config,
                results=[tagged_code],
                processed_files=1,
                skipped_files=[]
            )
            
            output_path = Path(tmpdir) / "output.md"
            OutputFormatter.save_to_file(result, output_path, format="markdown")
            
            assert output_path.exists()
            content = output_path.read_text(encoding='utf-8')
            assert "# 代码标签提取报告" in content
    
    def test_format_with_skipped_files(self) -> None:
        """测试包含跳过文件的格式化"""
        config = ExtractorConfig(
            tag="TODO:",
            target_path=Path(__file__).parent
        )
        
        result = ExtractionResult(
            config=config,
            results=[],
            processed_files=1,
            skipped_files=["test1.py: 语法错误", "test2.py: 编码错误"]
        )
        
        markdown = OutputFormatter._format_markdown(result)
        
        assert "**跳过文件**: 2" in markdown
        assert "跳过的文件" in markdown
        assert "test1.py: 语法错误" in markdown
        assert "test2.py: 编码错误" in markdown
    
    def test_format_multiple_files(self) -> None:
        """测试多个文件的格式化"""
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
            file_path=Path("test2.py"),
            name="func2",
            line_number=20,
            code="def func2(): pass",
            node_type="function"
        )
        
        result = ExtractionResult(
            config=config,
            results=[tagged_code1, tagged_code2],
            processed_files=2,
            skipped_files=[]
        )
        
        markdown = OutputFormatter._format_markdown(result)
        
        assert "test1.py" in markdown
        assert "test2.py" in markdown
        assert "func1" in markdown
        assert "func2" in markdown