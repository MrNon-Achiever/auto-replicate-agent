"""
工具函数模块
提供智能体复刻项目所需的核心工具
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ToolExecutor:
    """工具执行器，管理所有可用工具"""

    def __init__(self, work_dir: str):
        """
        初始化工具执行器

        Args:
            work_dir: 工作目录，所有文件操作都在此目录下进行
        """
        self.work_dir = Path(work_dir).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def read_file(self, path: str) -> Dict:
        """
        读取文件内容

        Args:
            path: 相对于工作目录的文件路径

        Returns:
            包含success和content的字典
        """
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {path}"}

            content = file_path.read_text(encoding="utf-8")
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "lines": content.count("\n") + 1
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str) -> Dict:
        """
        写入文件内容

        Args:
            path: 相对于工作目录的文件路径
            content: 文件内容

        Returns:
            包含success的字典
        """
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(file_path.relative_to(self.work_dir)),
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_command(self, cmd: str, timeout: int = 60) -> Dict:
        """
        执行命令

        Args:
            cmd: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            包含stdout、stderr和returncode的字典
        """
        import time

        # 安全检查：禁止危险命令
        dangerous_commands = [
            "rm -rf /", "rm -rf /*", "sudo rm", "mkfs",
            "dd if=", ":(){:|:&};:", "chmod -R 777 /"
        ]
        for dangerous in dangerous_commands:
            if dangerous in cmd:
                return {
                    "success": False,
                    "error": f"危险命令被拒绝: {cmd}"
                }

        # 日志：显示命令执行信息
        print(f"\n[命令执行] {cmd}")
        print(f"  超时时间: {timeout}秒")
        print(f"  工作目录: {self.work_dir}")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            elapsed_time = time.time() - start_time

            # 日志：显示执行结果
            print(f"  执行时间: {elapsed_time:.2f}秒")
            print(f"  返回码: {result.returncode}")

            if result.stdout:
                print(f"  标准输出: {result.stdout[:200]}{'...' if len(result.stdout) > 200 else ''}")
            if result.stderr:
                print(f"  标准错误: {result.stderr[:200]}{'...' if len(result.stderr) > 200 else ''}")

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "error": result.stderr if result.returncode != 0 else None,
                "elapsed_time": elapsed_time
            }
        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            print(f"  ❌ 命令超时（{timeout}秒）")
            return {
                "success": False,
                "error": f"命令超时（{timeout}秒）: {cmd}",
                "elapsed_time": elapsed_time
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"  ❌ 命令执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "elapsed_time": elapsed_time
            }

    def list_files(self, path: str = ".", max_depth: int = 3) -> Dict:
        """
        列出目录结构

        Args:
            path: 相对于工作目录的路径
            max_depth: 最大递归深度

        Returns:
            包含文件树的字典
        """
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.exists():
                return {"success": False, "error": f"目录不存在: {path}"}

            tree = self._build_tree(dir_path, max_depth)
            return {"success": True, "tree": tree}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_file(self, path: str, old_content: str, new_content: str) -> Dict:
        """
        编辑文件，替换指定内容

        Args:
            path: 相对于工作目录的文件路径
            old_content: 要替换的原内容（必须精确匹配）
            new_content: 替换后的新内容

        Returns:
            包含success的字典
        """
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {path}"}

            content = file_path.read_text(encoding="utf-8")

            if old_content not in content:
                return {"success": False, "error": f"未找到要替换的内容，请确保 old_content 精确匹配文件中的文本"}

            count = content.count(old_content)
            new_file_content = content.replace(old_content, new_content, 1)
            file_path.write_text(new_file_content, encoding="utf-8")

            return {
                "success": True,
                "path": str(file_path.relative_to(self.work_dir)),
                "replacements": 1,
                "total_occurrences": count
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict:
        """
        删除文件

        Args:
            path: 相对于工作目录的文件路径

        Returns:
            包含success的字典
        """
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {path}"}

            if file_path.is_dir():
                return {"success": False, "error": f"这是一个目录，请使用 run_command 执行 rm -rf 来删除目录"}

            file_path.unlink()
            return {
                "success": True,
                "path": str(file_path.relative_to(self.work_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_push(self, repo_name: str, description: str = "", private: bool = False) -> Dict:
        """
        创建新仓库并推送到GitHub

        Args:
            repo_name: 仓库名称
            description: 仓库描述
            private: 是否私有仓库

        Returns:
            包含success和repo_url的字典
        """
        import requests

        try:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                return {"success": False, "error": "未配置GITHUB_TOKEN"}

            github_user = os.environ.get("GITHUB_USER")
            if not github_user:
                return {"success": False, "error": "未配置GITHUB_USER"}

            # 日志：显示推送信息
            print(f"\n[GitHub推送] 开始")
            print(f"  仓库名: {repo_name}")
            print(f"  用户: {github_user}")
            print(f"  私有: {private}")

            # 步骤1：创建新仓库
            print(f"  正在创建仓库...")
            create_url = "https://api.github.com/user/repos"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "name": repo_name,
                "description": description or f"Auto cloned by Agent",
                "private": private,
                "auto_init": False
            }

            response = requests.post(create_url, headers=headers, json=data)

            if response.status_code == 201:
                print(f"  ✅ 仓库创建成功")
            elif response.status_code == 422:
                print(f"  ⚠️ 仓库已存在，将覆盖推送")
            else:
                return {
                    "success": False,
                    "error": f"创建仓库失败: {response.status_code} - {response.text}"
                }

            # 步骤2：初始化git仓库
            print(f"  正在初始化git仓库...")
            self.run_command("git init")
            self.run_command("git add .")
            self.run_command('git commit -m "Auto cloned by Agent"')

            # 步骤3：添加远程仓库并推送
            print(f"  正在推送到远程仓库...")
            remote_url = f"https://{token}@github.com/{github_user}/{repo_name}.git"
            self.run_command(f"git remote remove origin")  # 先移除已有的remote
            self.run_command(f"git remote add origin {remote_url}")
            self.run_command("git branch -M main")
            result = self.run_command("git push -u origin main --force")

            if result["success"]:
                repo_url = f"https://github.com/{github_user}/{repo_name}"
                print(f"  ✅ 推送成功")
                print(f"  仓库地址: {repo_url}")
                print(f"[GitHub推送] 完成\n")

                return {
                    "success": True,
                    "repo_url": repo_url
                }
            else:
                return {
                    "success": False,
                    "error": f"推送失败: {result.get('error', '未知错误')}"
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resolve_path(self, path: str) -> Path:
        """解析路径，确保在工作目录内"""
        resolved = (self.work_dir / path).resolve()
        if not str(resolved).startswith(str(self.work_dir)):
            raise ValueError(f"路径越界: {path}")
        return resolved

    def _build_tree(self, path: Path, max_depth: int, current_depth: int = 0) -> Dict:
        """构建目录树"""
        if current_depth >= max_depth:
            return {"name": path.name, "type": "dir", "children": [], "truncated": True}

        children = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    children.append(self._build_tree(item, max_depth, current_depth + 1))
                else:
                    children.append({
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size
                    })
        except PermissionError:
            pass

        return {
            "name": path.name,
            "type": "dir",
            "children": children
        }

    def get_tools_definition(self) -> List[Dict]:
        """获取所有工具的定义（OpenAI Function Calling格式）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取文件内容。用于查看代码、配置文件等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径（相对于工作目录）"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "写入文件内容。用于创建或修改代码文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径（相对于工作目录）"
                            },
                            "content": {
                                "type": "string",
                                "description": "文件内容"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "执行shell命令。用于安装依赖、运行测试、编译代码等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cmd": {
                                "type": "string",
                                "description": "要执行的命令"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "超时时间（秒），默认60"
                            }
                        },
                        "required": ["cmd"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "列出目录结构。用于了解项目文件组织。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "目录路径（相对于工作目录），默认为当前目录"
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "最大递归深度，默认3"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "编辑文件，精确替换指定内容。用于修改代码中的某一段，比 write_file 更高效（无需重写整个文件）。old_content 必须与文件中的文本完全一致，包括缩进和换行。只替换第一次出现的内容。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径（相对于工作目录）"
                            },
                            "old_content": {
                                "type": "string",
                                "description": "要替换的原内容，必须与文件中的文本精确匹配"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "替换后的新内容"
                            }
                        },
                        "required": ["path", "old_content", "new_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "删除指定文件。只能删除文件，不能删除目录。如需删除目录请使用 run_command。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "要删除的文件路径（相对于工作目录）"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_push",
                    "description": "创建新仓库并推送代码到GitHub。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "repo_name": {
                                "type": "string",
                                "description": "仓库名称"
                            },
                            "description": {
                                "type": "string",
                                "description": "仓库描述"
                            },
                            "private": {
                                "type": "boolean",
                                "description": "是否私有仓库，默认false"
                            }
                        },
                        "required": ["repo_name"]
                    }
                }
            }
        ]
