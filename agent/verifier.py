"""
代码验证模块
严格验证生成的代码质量
"""

import ast
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class VerificationResult:
    """验证结果"""
    success: bool
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CodeVerifier:
    """代码验证器 - 严格模式"""

    def __init__(self, work_dir: str):
        """
        初始化验证器

        Args:
            work_dir: 工作目录
        """
        self.work_dir = Path(work_dir).resolve()

    def verify_file(self, file_path: str) -> VerificationResult:
        """
        验证单个文件

        Args:
            file_path: 文件路径（相对于工作目录）

        Returns:
            验证结果
        """
        full_path = self.work_dir / file_path
        checks_passed = []
        checks_failed = []
        errors = []
        warnings = []

        if not full_path.exists():
            return VerificationResult(
                success=False,
                checks_passed=[],
                checks_failed=["file_exists"],
                errors=[f"文件不存在: {file_path}"],
                warnings=[]
            )

        suffix = full_path.suffix.lower()

        if suffix == ".py":
            result = self._verify_python(full_path, file_path)
        elif suffix in [".js", ".ts", ".jsx", ".tsx"]:
            result = self._verify_javascript(full_path, file_path)
        elif suffix == ".json":
            result = self._verify_json(full_path, file_path)
        else:
            result = self._verify_generic(full_path, file_path)

        return result

    def verify_project(self) -> VerificationResult:
        """
        验证整个项目

        Returns:
            验证结果
        """
        all_checks_passed = []
        all_checks_failed = []
        all_errors = []
        all_warnings = []

        code_files = []
        for ext in ["*.py", "*.js", "*.ts", "*.json"]:
            code_files.extend(self.work_dir.rglob(ext))

        code_files = [
            f for f in code_files
            if "node_modules" not in str(f) and
               ".git" not in str(f) and
               "venv" not in str(f) and
               "target_repo" not in str(f) and
               "output" not in str(f)
        ]

        for file_path in code_files:
            relative_path = str(file_path.relative_to(self.work_dir))
            result = self.verify_file(relative_path)

            all_checks_passed.extend(
                [f"{relative_path}: {check}" for check in result.checks_passed]
            )
            all_checks_failed.extend(
                [f"{relative_path}: {check}" for check in result.checks_failed]
            )
            all_errors.extend(
                [f"{relative_path}: {error}" for error in result.errors]
            )
            all_warnings.extend(
                [f"{relative_path}: {warning}" for warning in result.warnings]
            )

        # 检查是否有入口文件
        entry_files = ["main.py", "app.py", "index.js", "index.ts", "package.json"]
        has_entry = any((self.work_dir / f).exists() for f in entry_files)
        if has_entry:
            all_checks_passed.append("entry_file_exists")
        else:
            all_warnings.append("未找到常见入口文件")

        # 检查是否有README
        readme_files = ["README.md", "readme.md", "README.txt"]
        has_readme = any((self.work_dir / f).exists() for f in readme_files)
        if has_readme:
            all_checks_passed.append("readme_exists")
        else:
            all_warnings.append("未找到README文件")

        return VerificationResult(
            success=len(all_errors) == 0,
            checks_passed=all_checks_passed,
            checks_failed=all_checks_failed,
            errors=all_errors,
            warnings=all_warnings
        )

    def verify_dependencies(self) -> VerificationResult:
        """验证依赖是否可安装"""
        checks_passed = []
        checks_failed = []
        errors = []
        warnings = []

        requirements_file = self.work_dir / "requirements.txt"
        if requirements_file.exists():
            result = subprocess.run(
                ["pip", "check"],
                cwd=str(self.work_dir),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                checks_passed.append("python_dependencies")
            else:
                checks_failed.append("python_dependencies")
                errors.append(f"Python依赖检查失败: {result.stderr}")

        package_json = self.work_dir / "package.json"
        if package_json.exists():
            node_modules = self.work_dir / "node_modules"
            if node_modules.exists():
                checks_passed.append("node_dependencies")
            else:
                warnings.append("node_modules不存在，需要运行npm install")

        return VerificationResult(
            success=len(errors) == 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            errors=errors,
            warnings=warnings
        )

    def _verify_python(self, file_path: Path, relative_path: str) -> VerificationResult:
        """验证Python文件 - 严格模式"""
        checks_passed = []
        checks_failed = []
        errors = []
        warnings = []

        try:
            content = file_path.read_text(encoding="utf-8")

            # 1. 语法检查
            try:
                ast.parse(content)
                checks_passed.append("python_syntax")
            except SyntaxError as e:
                checks_failed.append("python_syntax")
                errors.append(f"Python语法错误: {e}")

            # 2. 编译检查
            result = subprocess.run(
                ["python", "-m", "py_compile", str(file_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                checks_passed.append("python_compile")
            else:
                checks_failed.append("python_compile")
                errors.append(f"Python编译错误: {result.stderr}")

            # 3. 检查括号匹配
            open_parens = content.count("(") - content.count(")")
            open_brackets = content.count("[") - content.count("]")
            open_braces = content.count("{") - content.count("}")
            if open_parens != 0 or open_brackets != 0 or open_braces != 0:
                warnings.append("可能存在未闭合的括号")

            # 4. 检查是否有import错误
            if "import" in content:
                try:
                    # 尝试编译检查import
                    result = subprocess.run(
                        ["python", "-c", f"import sys; sys.path.insert(0, '{self.work_dir}'); exec(open('{file_path}').read().split('if __name__')[0])"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0 and "SyntaxError" not in result.stderr:
                        warnings.append(f"可能存在导入问题: {result.stderr[:100]}")
                except:
                    pass

            # 5. 检查代码复杂度（简单检查）
            lines = content.split("\n")
            if len(lines) > 500:
                warnings.append(f"文件较长（{len(lines)}行），建议拆分")

            # 6. 检查是否有TODO/FIXME
            for i, line in enumerate(lines, 1):
                if "TODO" in line or "FIXME" in line:
                    warnings.append(f"第{i}行有TODO/FIXME注释")

        except Exception as e:
            errors.append(f"验证失败: {e}")

        return VerificationResult(
            success=len(errors) == 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            errors=errors,
            warnings=warnings
        )

    def _verify_javascript(self, file_path: Path, relative_path: str) -> VerificationResult:
        """验证JavaScript文件"""
        checks_passed = []
        checks_failed = []
        errors = []
        warnings = []

        try:
            content = file_path.read_text(encoding="utf-8")

            # 基本语法检查
            result = subprocess.run(
                ["node", "--check", str(file_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                checks_passed.append("javascript_syntax")
            else:
                checks_failed.append("javascript_syntax")
                errors.append(f"JavaScript语法错误: {result.stderr}")

            # 检查括号匹配
            open_parens = content.count("(") - content.count(")")
            open_brackets = content.count("[") - content.count("]")
            open_braces = content.count("{") - content.count("}")
            if open_parens != 0 or open_brackets != 0 or open_braces != 0:
                warnings.append("可能存在未闭合的括号")

        except FileNotFoundError:
            warnings.append("未找到node命令，跳过JavaScript验证")
        except Exception as e:
            errors.append(f"验证失败: {e}")

        return VerificationResult(
            success=len(errors) == 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            errors=errors,
            warnings=warnings
        )

    def _verify_json(self, file_path: Path, relative_path: str) -> VerificationResult:
        """验证JSON文件"""
        checks_passed = []
        checks_failed = []
        errors = []

        try:
            content = file_path.read_text(encoding="utf-8")
            json.loads(content)
            checks_passed.append("json_syntax")
        except json.JSONDecodeError as e:
            checks_failed.append("json_syntax")
            errors.append(f"JSON语法错误: {e}")
        except Exception as e:
            errors.append(f"验证失败: {e}")

        return VerificationResult(
            success=len(errors) == 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            errors=errors,
            warnings=[]
        )

    def _verify_generic(self, file_path: Path, relative_path: str) -> VerificationResult:
        """通用文件验证"""
        checks_passed = []
        warnings = []

        try:
            file_path.read_text(encoding="utf-8")
            checks_passed.append("file_readable")
        except UnicodeDecodeError:
            warnings.append("文件可能包含非文本内容")

        return VerificationResult(
            success=True,
            checks_passed=checks_passed,
            checks_failed=[],
            errors=[],
            warnings=warnings
        )

    def format_result(self, result: VerificationResult) -> str:
        """格式化验证结果"""
        lines = []

        if result.success:
            lines.append("✅ 验证通过")
        else:
            lines.append("❌ 验证失败")

        if result.checks_passed:
            lines.append("\n通过的检查:")
            for check in result.checks_passed:
                lines.append(f"  ✓ {check}")

        if result.checks_failed:
            lines.append("\n失败的检查:")
            for check in result.checks_failed:
                lines.append(f"  ✗ {check}")

        if result.errors:
            lines.append("\n错误:")
            for error in result.errors:
                lines.append(f"  ! {error}")

        if result.warnings:
            lines.append("\n警告:")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)
