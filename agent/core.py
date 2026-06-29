"""
Agent Loop 核心模块
实现智能体的主循环逻辑，使用真正的工具调用
高性能模式：深度分析、高质量代码生成、严格验证
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Callable

from .tools import ToolExecutor
from .verifier import CodeVerifier
from .llm import get_llm_client
from . import config


class CloneAgent:
    """复刻智能体 - 高性能模式"""

    def __init__(self, work_dir: str = None):
        """
        初始化智能体

        Args:
            work_dir: 工作目录，默认使用配置文件中的值
        """
        self.work_dir = Path(work_dir or config.WORK_DIR).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.tools = ToolExecutor(str(self.work_dir))
        self.verifier = CodeVerifier(str(self.work_dir))
        self.llm = get_llm_client()

        # 获取工具定义
        self.tools_definition = self.tools.get_tools_definition()

        # 状态
        self.iteration = 0
        self.fix_attempts = 0
        self.is_running = False
        self.current_task = None

        # 多仓库支持：当前序号和目录
        self.current_index = self._get_next_index()
        self.current_target_dir = f"target_repo_{self.current_index}"
        self.current_output_dir = f"output_{self.current_index}"

        # 回调函数
        self.on_progress: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None

    def _get_next_index(self) -> int:
        """
        获取下一个可用的序号

        Returns:
            下一个序号
        """
        max_index = 0

        # 检查已存在的 target_repo_N 目录
        for item in self.work_dir.iterdir():
            if item.is_dir():
                name = item.name
                if name.startswith("target_repo_"):
                    try:
                        index = int(name.split("_")[-1])
                        max_index = max(max_index, index)
                    except ValueError:
                        pass

        return max_index + 1

    def _execute_tool(self, name: str, arguments: Dict) -> Dict:
        """
        执行工具调用

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if name == "read_file":
            return self.tools.read_file(arguments.get("path", ""))
        elif name == "write_file":
            # 写入文件时，自动添加 output_N 前缀
            original_path = arguments.get("path", "")
            output_path = f"{self.current_output_dir}/{original_path}"
            return self.tools.write_file(
                output_path,
                arguments.get("content", "")
            )
        elif name == "run_command":
            # 执行命令时，如果需要进入输出目录，可以使用 cd 命令
            # 或者让 LLM 在命令中指定完整路径
            return self.tools.run_command(
                arguments.get("cmd", ""),
                arguments.get("timeout", 120)
            )
        elif name == "edit_file":
            # 编辑文件时，自动添加 output_N 前缀
            original_path = arguments.get("path", "")
            output_path = f"{self.current_output_dir}/{original_path}"
            return self.tools.edit_file(
                output_path,
                arguments.get("old_content", ""),
                arguments.get("new_content", "")
            )
        elif name == "delete_file":
            # 删除文件时，自动添加 output_N 前缀
            original_path = arguments.get("path", "")
            output_path = f"{self.current_output_dir}/{original_path}"
            return self.tools.delete_file(output_path)
        elif name == "list_files":
            return self.tools.list_files(
                arguments.get("path", "."),
                arguments.get("max_depth", 5)
            )
        elif name == "git_push":
            return self.tools.git_push(
                arguments.get("repo_name", ""),
                arguments.get("description", ""),
                arguments.get("private", False)
            )
        else:
            return {"success": False, "error": f"未知工具: {name}"}

    def clone_repo(self, repo_url: str) -> Dict:
        """
        复刻指定仓库

        Args:
            repo_url: 仓库URL

        Returns:
            复刻结果
        """
        self.is_running = True
        self.current_task = repo_url

        try:
            # 创建输出目录
            output_dir = self.work_dir / self.current_output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            self._report_progress(f"当前任务序号: {self.current_index}")
            self._report_progress(f"目标仓库目录: {self.current_target_dir}")
            self._report_progress(f"输出代码目录: {self.current_output_dir}")

            # 步骤1：克隆目标仓库
            self._report_progress("正在克隆目标仓库...")
            clone_result = self._clone_target_repo(repo_url)
            if not clone_result["success"]:
                return {"success": False, "error": f"克隆失败: {clone_result['error']}"}

            # 步骤2：深度分析项目
            self._report_progress("正在深度分析项目结构和功能...")
            analysis = self._deep_analyze_project()
            if not analysis["success"]:
                return {"success": False, "error": f"分析失败: {analysis['error']}"}

            # 步骤3：规划简化版本
            self._report_progress("正在规划高质量简化版本...")
            plan = self._plan_high_quality_simplification(analysis)
            if not plan["success"]:
                return {"success": False, "error": f"规划失败: {plan['error']}"}

            # 步骤4：生成高质量代码
            self._report_progress("正在生成高质量代码...")
            generation = self._generate_high_quality_code(plan["plan"], analysis)
            if not generation["success"]:
                return {"success": False, "error": f"生成失败: {generation['error']}"}

            # 步骤5：严格验证和修复
            self._report_progress("正在严格验证和修复...")
            verification = self._strict_verify_and_fix()
            if not verification["success"]:
                return {"success": False, "error": f"验证失败: {verification['error']}"}

            # 步骤6：集成测试
            self._report_progress("正在执行集成测试...")
            integration = self._integration_test()
            if not integration["success"]:
                self._report_progress(f"集成测试警告: {integration.get('error', '未知错误')}")

            # 步骤7：清理无用文件
            self._report_progress("正在清理无用文件...")
            cleanup = self._cleanup_unnecessary_files()
            if not cleanup["success"]:
                self._report_progress(f"清理警告: {cleanup.get('error', '未知错误')}")

            # 步骤8：推送到GitHub
            self._report_progress("正在推送到GitHub...")
            push_result = self._push_to_github(repo_url)
            if push_result["success"]:
                self._report_progress(f"推送成功: {push_result.get('repo_url', '')}")
            else:
                self._report_progress(f"推送失败: {push_result.get('error', '未知错误')}")

            # 步骤9：打包结果
            self._report_progress("正在打包结果...")
            result = self._package_result(repo_url, push_result)

            self._report_progress("复刻完成！")
            return result

        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            return {"success": False, "error": str(e)}
        finally:
            self.is_running = False

    def _clone_target_repo(self, repo_url: str) -> Dict:
        """克隆目标仓库"""
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        clone_dir = self.work_dir / self.current_target_dir

        if clone_dir.exists():
            try:
                import stat
                def remove_readonly(func, path, excinfo):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                shutil.rmtree(clone_dir, onerror=remove_readonly)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"无法删除已存在的目录: {str(e)}。请手动删除 {clone_dir} 后重试。"
                }

        result = self.tools.run_command(
            f"git clone --depth 1 {repo_url} {self.current_target_dir}",
            timeout=180
        )

        if not result["success"]:
            return result

        if not clone_dir.exists():
            return {"success": False, "error": "克隆目录不存在"}

        return {"success": True, "repo_name": repo_name}

    def _deep_analyze_project(self) -> Dict:
        """深度分析项目，使用工具调用"""

        system_prompt = """你是一个高级代码分析师，擅长深度理解项目架构和功能。

你的任务是全面分析一个项目，为后续完整复刻做准备。

你可以使用以下工具：
- read_file(path): 读取文件内容，深入了解代码实现
- list_files(path, max_depth): 列出目录结构，了解项目组织
- run_command(cmd): 执行命令，如查看依赖、检查代码等

分析要求：

1. **技术栈识别**（必须准确）
   - 后端语言和框架（Python/Django/Flask/FastAPI, Node.js/Express/Koa等）
   - 前端框架（Vue/React/Angular, 或纯HTML/CSS/JS）
   - 数据库（MySQL/PostgreSQL/MongoDB/SQLite等）
   - 其他中间件（Redis、消息队列等）

2. **项目类型判断**
   - 纯后端服务（API服务、CLI工具）
   - 全栈应用（前后端一体）
   - 前端应用（纯前端）
   - 微服务架构

3. **前端分析**（如果有前端）
   - 前端框架和版本
   - 页面路由结构
   - 组件划分
   - API调用方式
   - UI库使用

4. **后端分析**
   - API接口列表
   - 数据库模型
   - 业务逻辑模块
   - 中间件配置

5. **核心功能识别**
   - 必须保留的核心功能
   - 可以简化的辅助功能
   - 可以删除的非核心功能

分析深度：
- 必须阅读所有关键文件的完整内容
- 理解前后端的交互方式
- 理解数据流转过程

请输出详细的分析报告，包含：
1. 项目概述
2. 技术栈详细分析
3. 项目类型（全栈/纯后端/纯前端）
4. 前端架构（如果有）
5. 后端架构
6. 数据库设计
7. API接口列表
8. 核心功能列表
9. 复刻方案建议

请开始深入分析。"""

        # 获取初始目录结构
        tree_result = self.tools.list_files(self.current_target_dir, max_depth=3)
        tree_str = json.dumps(tree_result.get("tree", {}), indent=2, ensure_ascii=False) if tree_result["success"] else "无法获取目录结构"

        # 读取README
        readme_content = ""
        target_dir = self.work_dir / self.current_target_dir
        for readme_name in ["README.md", "readme.md", "README.txt", "README"]:
            readme_path = target_dir / readme_name
            if readme_path.exists():
                try:
                    readme_content = readme_path.read_text(encoding="utf-8")[:5000]
                except:
                    pass
                break

        # 读取配置文件
        config_files = []
        for config_name in ["package.json", "requirements.txt", "setup.py", "pyproject.toml", "Cargo.toml", "go.mod"]:
            config_path = target_dir / config_name
            if config_path.exists():
                try:
                    config_files.append(f"=== {config_name} ===\n{config_path.read_text(encoding='utf-8')[:2000]}")
                except:
                    pass

        user_message = f"""请深度分析以下项目：

项目目录结构：
{tree_str}

README内容：
{readme_content if readme_content else "无README文件"}

配置文件：
{chr(10).join(config_files) if config_files else "无配置文件"}

注意：原始代码在 {self.current_target_dir} 目录下。
读取文件时请使用路径：{self.current_target_dir}/文件名

请使用工具深入分析每个关键文件，输出详细的分析报告。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.chat_with_tools(
            messages=messages,
            tools=self.tools_definition,
            tool_executor=self._execute_tool,
            max_rounds=config.MAX_ROUNDS_ANALYZE
        )

        if not response["success"]:
            return response

        return {"success": True, "analysis": response["content"]}

    def _plan_high_quality_simplification(self, analysis: Dict) -> Dict:
        """规划完整复刻方案"""

        system_prompt = """你是一个高级软件架构师，擅长设计完整的项目复刻方案。

你的任务是基于项目分析，规划一个**完整复刻**方案，而不是简化版本。

⚠️ 核心原则：
1. **完整复刻** - 保留原项目的核心功能和架构，不是做简化版
2. **保留前端** - 如果原项目有前端，必须规划前端复刻
3. **技术栈匹配** - 使用与原项目相同或相似的技术栈
4. **可直接运行** - 复刻的项目必须能直接运行

你可以使用以下工具：
- read_file(path): 读取原始代码，理解实现细节
- list_files(path): 查看目录结构
- run_command(cmd): 执行命令获取信息

规划要求：

1. **项目类型判断**
   - 全栈应用（有前后端）
   - 纯后端服务
   - 纯前端应用

2. **技术栈规划**
   - 后端框架：与原项目一致或相似
   - 前端方案：
     * 原项目有Vue/React/Angular → 用Streamlit替代
     * 原项目有纯HTML/CSS/JS → 保留原样
     * 原项目无前端 → 根据需要添加
   - 数据库：与原项目一致

3. **功能规划**
   - 列出必须保留的核心功能
   - 列出可以保留的辅助功能
   - 列出可以删除的非核心功能

4. **文件结构规划**
   - 后端文件结构
   - 前端文件结构（如果有）
   - 配置文件

5. **依赖规划**
   - 后端依赖（requirements.txt/package.json）
   - 前端依赖（如果有）

6. **启动方式规划**
   - 如何启动后端
   - 如何启动前端（如果有）
   - 如何访问应用

请输出详细的规划文档，包含：
1. 项目类型
2. 技术栈选择
3. 功能清单（保留/删除）
4. 文件结构设计
5. 依赖清单
6. 启动和访问方式
7. 实现顺序

请使用read_file工具深入理解原始代码，然后输出完整的复刻规划。"""

        user_message = f"""请基于以下分析报告，规划高质量的简化版本：

{analysis.get('analysis', '无分析报告')}

注意：原始代码在 {self.current_target_dir} 目录下。
读取文件时请使用路径：{self.current_target_dir}/文件名

请使用工具深入理解原始代码，然后输出详细的规划文档。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.chat_with_tools(
            messages=messages,
            tools=self.tools_definition,
            tool_executor=self._execute_tool,
            max_rounds=config.MAX_ROUNDS_ANALYZE
        )

        if not response["success"]:
            return response

        plan = self._parse_plan(response["content"])
        return {"success": True, "plan": plan}

    def _parse_plan(self, plan_text: str) -> Dict:
        """解析规划结果"""
        try:
            json_start = plan_text.find("{")
            json_end = plan_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = plan_text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass

        return {
            "project_name": "simplified_project",
            "description": "简化版项目",
            "features": ["核心功能"],
            "files": [
                {"path": "main.py", "description": "主程序入口"},
                {"path": "README.md", "description": "项目说明"}
            ],
            "dependencies": []
        }

    def _generate_high_quality_code(self, plan: Dict, analysis: Dict) -> Dict:
        """生成高质量代码"""

        system_prompt = """你是一个高级全栈开发专家，擅长复刻完整的项目。

你的任务是根据分析报告和规划，**完整复刻**原项目，而不是生成简化版。

⚠️⚠️⚠️ 最重要的要求 ⚠️⚠️⚠️
你必须使用write_file工具来生成代码文件！
不要只是在回复中描述代码或输出代码块，必须实际调用write_file工具写入文件！
每生成一个文件，都必须调用一次write_file工具！

⚠️ 重要原则：
1. **不要简化** - 复刻的项目应该保留原项目的核心功能和架构
2. **保留前端** - 如果原项目有前端，必须保留前端（可以用Streamlit替代复杂前端）
3. **技术栈匹配** - 使用与原项目相同或相似的技术栈
4. **完整可运行** - 生成的项目必须能直接运行，包含所有必要文件

你可以使用以下工具：
- read_file(path): 读取原始代码，参考其实现
- write_file(path, content): 写入生成的代码文件（你必须使用这个工具！）
- edit_file(path, old_content, new_content): 编辑文件，精确替换指定内容（比 write_file 更高效，无需重写整个文件）
- delete_file(path): 删除指定文件
- run_command(cmd): 执行命令，如安装依赖、运行测试
- list_files(path): 查看目录结构

复刻策略：

1. **全栈应用**（原项目有前后端）
   - 后端：保留原有框架（Django/Flask/FastAPI/Express等）
   - 前端：
     * 如果原项目是Vue/React/Angular → 用Streamlit替代（更简单）
     * 如果原项目是纯HTML/CSS/JS → 保留原样
     * 如果原项目没有前端 → 根据需要添加Streamlit界面

2. **纯后端服务**
   - 保留原有框架和API设计
   - 添加必要的CLI界面或简单Web界面

3. **前端应用**
   - 保留原有框架
   - 简化复杂组件，但保留核心功能

代码质量要求：
1. 完整性 - 每个文件必须是完整的，可以直接运行
2. 健壮性 - 包含完整的错误处理
3. 可读性 - 清晰的命名、充分的注释
4. 可运行性 - 包含requirements.txt/package.json，能直接安装运行

文件生成顺序：
1. 先生成配置文件（requirements.txt, .env.example等）
2. 再生成后端代码
3. 再生成前端代码（如果有）
4. 最后生成启动脚本和文档

请逐个使用write_file工具生成每个文件，确保项目完整可运行。"""

        files_desc = "\n".join([
            f"- {f['path']}: {f['description']}"
            for f in plan.get("files", [])
        ])

        user_message = f"""请根据以下规划生成高质量代码：

项目名称：{plan.get('project_name', 'unknown')}
项目描述：{plan.get('description', 'unknown')}
保留功能：{', '.join(plan.get('features', []))}
依赖列表：{', '.join(plan.get('dependencies', [])) if plan.get('dependencies') else '无'}

需要生成的文件：
{files_desc}

⚠️ 重要提示：
1. 你必须使用write_file工具来生成代码文件！不要只是描述代码，必须实际调用write_file写入文件！
2. 原始代码在 {self.current_target_dir} 目录下，读取时请使用路径：{self.current_target_dir}/文件名
3. 生成的代码会自动保存到 {self.current_output_dir} 目录，写入时直接使用文件名即可

请先使用read_file阅读所有相关的原始代码文件，理解其实现，然后逐个使用write_file工具生成高质量的代码文件。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.chat_with_tools(
            messages=messages,
            tools=self.tools_definition,
            tool_executor=self._execute_tool,
            max_rounds=config.MAX_ROUNDS_GENERATE
        )

        if not response["success"]:
            return response

        # 检查生成的文件
        generated_files = []
        for file_info in plan.get("files", []):
            file_path = self.work_dir / self.current_output_dir / file_info["path"]
            if file_path.exists():
                generated_files.append(file_info["path"])

        # 日志：显示生成结果
        print(f"\n{'='*60}")
        print(f"[代码生成] 完成")
        print(f"  规划文件数: {len(plan.get('files', []))}")
        print(f"  实际生成数: {len(generated_files)}")
        print(f"  生成的文件:")
        for f in generated_files:
            print(f"    - {f}")
        print(f"{'='*60}\n")

        # 如果没有生成任何文件，返回失败
        if not generated_files:
            return {"success": False, "error": "代码生成失败：没有生成任何文件"}

        return {"success": True, "files": generated_files}

    def _strict_verify_and_fix(self) -> Dict:
        """严格验证和修复代码"""
        fix_count = 0

        # 临时切换验证器的工作目录到 output_N
        original_verifier_dir = self.verifier.work_dir
        output_dir = self.work_dir / self.current_output_dir
        self.verifier.work_dir = output_dir

        try:
            while fix_count < config.MAX_FIX_ATTEMPTS:
                verify_result = self.verifier.verify_project()

                if verify_result.success:
                    return {"success": True}

                errors = verify_result.errors
                if not errors:
                    return {"success": True}

                self._report_progress(f"发现 {len(errors)} 个错误，正在修复... (尝试 {fix_count + 1}/{config.MAX_FIX_ATTEMPTS})")

                fix_result = self._fix_errors_strict(errors)
                if not fix_result["success"]:
                    return fix_result

                fix_count += 1

            return {
                "success": False,
                "error": f"超过最大修复尝试次数 ({config.MAX_FIX_ATTEMPTS})"
            }
        finally:
            # 恢复验证器的工作目录
            self.verifier.work_dir = original_verifier_dir

    def _fix_errors_strict(self, errors: List[str]) -> Dict:
        """严格修复错误"""

        system_prompt = """你是一个高级代码修复专家，擅长修复各种代码错误。

你的任务是修复代码中的错误，确保代码能正常运行。

修复要求：
1. 必须理解错误的根本原因
2. 修复必须是完整的，不能只修复表面问题
3. 修复后必须验证代码能正常运行
4. 不能引入新的问题

你可以使用以下工具：
- read_file(path): 读取出错的文件，理解代码结构
- write_file(path, content): 写入修复后的完整代码
- edit_file(path, old_content, new_content): 编辑文件，精确替换指定内容（推荐用于局部修复，比 write_file 更高效）
- delete_file(path): 删除不需要的文件
- run_command(cmd): 执行命令验证修复（如语法检查、运行测试）
- list_files(path): 查看目录结构

修复流程：
1. 用read_file读取出错的文件
2. 分析错误原因（语法错误、逻辑错误、依赖问题等）
3. 用write_file写入修复后的完整代码（必须是完整文件，不是片段）
4. 用run_command验证修复（如 python -m py_compile 文件名）
5. 确认修复成功后继续下一个错误

常见错误类型：
- 语法错误：检查括号、缩进、冒号等
- 导入错误：检查模块名、路径、依赖
- 类型错误：检查变量类型、函数参数
- 逻辑错误：检查条件判断、循环逻辑

请逐个修复错误，确保每个修复都经过验证。"""

        errors_desc = "\n".join([f"- {error}" for error in errors[:10]])

        user_message = f"""请修复以下错误：

{errors_desc}

注意：生成的代码文件在 {self.current_output_dir} 目录下。
读取文件时请使用路径：{self.current_output_dir}/文件名
写入文件时直接使用文件名（系统会自动添加目录前缀）。

请使用工具读取出错的文件，分析错误原因，然后写入修复后的完整代码。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.chat_with_tools(
            messages=messages,
            tools=self.tools_definition,
            tool_executor=self._execute_tool,
            max_rounds=config.MAX_ROUNDS_FIX
        )

        if not response["success"]:
            return response

        return {"success": True}

    def _integration_test(self) -> Dict:
        """集成测试"""

        system_prompt = """你是一个测试专家，负责验证复刻的项目是否能正常运行。

你的任务是执行集成测试，确保项目质量。

你可以使用以下工具：
- read_file(path): 读取代码文件，理解实现
- edit_file(path, old_content, new_content): 编辑文件，修复问题
- delete_file(path): 删除不需要的文件
- run_command(cmd): 执行测试命令
- list_files(path): 查看目录结构

测试流程：
1. 检查项目结构是否完整
2. 检查依赖是否正确安装
3. 尝试运行项目
4. 验证核心功能是否正常
5. 输出测试报告

测试要求：
- 必须测试项目的启动是否正常
- 必须测试核心功能是否可用
- 记录所有发现的问题
- 给出改进建议

请执行测试并输出详细的测试报告。"""

        user_message = f"""请对当前项目执行集成测试：

注意：生成的代码文件在 {self.current_output_dir} 目录下。
读取文件时请使用路径：{self.current_output_dir}/文件名
执行命令时请先进入 {self.current_output_dir} 目录。

测试步骤：
1. 检查项目结构
2. 检查依赖
3. 尝试运行项目
4. 验证核心功能
5. 输出测试报告

请使用工具执行测试。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.chat_with_tools(
            messages=messages,
            tools=self.tools_definition,
            tool_executor=self._execute_tool,
            max_rounds=50
        )

        if not response["success"]:
            return response

        return {"success": True, "report": response["content"]}

    def _cleanup_unnecessary_files(self) -> Dict:
        """清理无用文件，只保留核心项目文件。LLM一次性决定删除列表，程序直接执行。"""

        # 获取所有文件（只在当前 output_N 目录下）
        output_dir = self.work_dir / self.current_output_dir
        all_files = []
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(output_dir))
                if ".git" not in relative_path:
                    all_files.append(relative_path)

        if not all_files:
            return {"success": True, "files": []}

        system_prompt = """你是一个代码清理专家。给你一个文件列表，你需要判断哪些文件应该删除。

删除规则：
1. 删除所有 .md 文件（README.md 除外）
2. 删除所有 .log 文件
3. 删除临时文件、缓存文件、__pycache__ 目录下的文件
4. 删除测试报告、规划文档（如 simplification_plan.md、health_analytics.log 等）
5. 删除 .pyc 文件

保留规则：
1. 保留所有代码文件（.py, .js, .ts, .html, .css 等）
2. 保留配置文件（requirements.txt, package.json, .env.example 等）
3. 保留 README.md
4. 保留必要的数据文件

你必须只返回一个 JSON 数组，包含要删除的文件路径，不要返回其他内容。
例如：["file1.md", "dir/file2.log"]
如果没有要删除的文件，返回空数组：[]"""

        user_message = f"""以下是项目中的文件列表，请返回要删除的文件路径 JSON 数组：

{chr(10).join(f'{f}' for f in all_files)}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.llm.chat(messages)

        if not response["success"]:
            return response

        # 解析 LLM 返回的 JSON 数组
        content = response["content"].strip()
        files_to_delete = []
        try:
            # 尝试从响应中提取 JSON 数组
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                files_to_delete = json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            self._report_progress("LLM 返回的删除列表解析失败，跳过清理")
            return {"success": True, "files": all_files}

        # 执行删除
        deleted_count = 0
        for file_name in files_to_delete:
            file_path = output_dir / file_name
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    self._report_progress(f"删除失败: {file_name} - {e}")

        # 统计剩余文件
        remaining_files = []
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(output_dir))
                if ".git" not in relative_path:
                    remaining_files.append(relative_path)

        print(f"\n{'='*60}")
        print(f"[文件清理] 完成")
        print(f"  清理前文件数: {len(all_files)}")
        print(f"  删除文件数: {deleted_count}")
        print(f"  清理后文件数: {len(remaining_files)}")
        print(f"  保留的文件:")
        for f in remaining_files:
            print(f"    - {f}")
        print(f"{'='*60}\n")

        return {"success": True, "files": remaining_files}

    def _push_to_github(self, original_repo_url: str) -> Dict:
        """推送到GitHub"""
        import re

        # 从原始URL提取仓库名
        # 例如：https://github.com/HuZhenhu/bishe2.0 -> bishe2.0
        match = re.search(r'github\.com/[^/]+/([^/]+?)(?:\.git)?$', original_repo_url)
        if match:
            original_name = match.group(1)
        else:
            original_name = "cloned-project"

        # 生成新仓库名
        repo_name = f"{original_name}-simplified"

        # 临时切换工作目录到 output_N
        original_work_dir = self.tools.work_dir
        output_dir = self.work_dir / self.current_output_dir
        self.tools.work_dir = output_dir

        try:
            # 调用git_push工具
            result = self.tools.git_push(
                repo_name=repo_name,
                description=f"Simplified version of {original_repo_url}",
                private=False
            )
        finally:
            # 恢复原始工作目录
            self.tools.work_dir = original_work_dir

        return result

    def _package_result(self, original_repo_url: str, push_result: Dict = None) -> Dict:
        """打包结果"""
        # 生成README
        readme_content = self._generate_readme(original_repo_url)
        output_dir = self.work_dir / self.current_output_dir
        readme_path = output_dir / "README.md"
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(readme_content, encoding="utf-8")

        # 收集生成的文件列表
        generated_files = []
        for file_path in output_dir.rglob("*"):
            if file_path.is_file() and ".git" not in str(file_path):
                generated_files.append(str(file_path.relative_to(output_dir)))

        result = {
            "success": True,
            "output_dir": str(output_dir),
            "target_dir": str(self.work_dir / self.current_target_dir),
            "index": self.current_index,
            "files": generated_files
        }

        # 添加推送结果
        if push_result:
            result["push"] = push_result
            if push_result.get("success"):
                result["repo_url"] = push_result.get("repo_url", "")

        return result

    def _generate_readme(self, original_repo_url: str) -> str:
        """生成README"""
        return f"""# 简化版项目

本项目是由AI智能体自动复刻生成的简化版本。

## 原始项目

{original_repo_url}

## 功能特性

- 保留了核心功能
- 简化了代码结构
- 去除了复杂依赖
- 优化了代码质量

## 安装依赖

```bash
# Python项目
pip install -r requirements.txt

# Node.js项目
npm install
```

## 使用方法

```bash
# Python项目
python main.py

# Node.js项目
node index.js
```

## 项目结构

```
├── main.py          # 主程序入口
├── README.md        # 项目说明
└── ...              # 其他文件
```

## 开发说明

本项目保留了原始项目的核心功能，但进行了以下简化：
- 去除了复杂的配置
- 简化了依赖关系
- 优化了代码结构
- 增加了代码注释

## 许可证

本项目仅供学习和研究使用，请遵守原始项目的开源许可证。

## 致谢

感谢原始项目作者的贡献。
"""

    def _report_progress(self, message: str):
        """报告进度"""
        if self.on_progress:
            self.on_progress(message)
        print(f"[Agent] {message}")

    def save_checkpoint(self):
        """保存检查点"""
        checkpoint_file = self.work_dir / "checkpoint.json"
        checkpoint = {
            "iteration": self.iteration,
            "fix_attempts": self.fix_attempts,
            "current_task": self.current_task
        }
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f)

    def load_checkpoint(self) -> bool:
        """加载检查点"""
        checkpoint_file = self.work_dir / "checkpoint.json"
        if not checkpoint_file.exists():
            return False

        try:
            with open(checkpoint_file, "r") as f:
                checkpoint = json.load(f)

            self.iteration = checkpoint.get("iteration", 0)
            self.fix_attempts = checkpoint.get("fix_attempts", 0)
            self.current_task = checkpoint.get("current_task")
            return True
        except:
            return False


def clone_repository(repo_url: str, work_dir: str = None) -> Dict:
    """
    复刻指定仓库（便捷函数）

    Args:
        repo_url: 仓库URL
        work_dir: 工作目录

    Returns:
        复刻结果
    """
    agent = CloneAgent(work_dir)
    return agent.clone_repo(repo_url)
