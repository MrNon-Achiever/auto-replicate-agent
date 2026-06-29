"""
推送到GitHub - 独立脚本
用于手动将指定目录的代码推送到GitHub仓库
支持代理：通过环境变量 HTTP_PROXY / HTTPS_PROXY 或 .env 中的 PROXY 配置
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_proxy() -> str:
    """
    获取代理地址，优先级：
    1. 环境变量 HTTPS_PROXY / HTTP_PROXY
    2. .env 中的 PROXY 配置
    """
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("PROXY", "")
    return proxy.strip()


def run_cmd(cmd: str, cwd: str, timeout: int = 120) -> dict:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stderr": f"命令超时（{timeout}秒）"}
    except Exception as e:
        return {"success": False, "stderr": str(e)}


def create_github_repo(token: str, user: str, repo_name: str, description: str, private: bool, proxies: dict) -> dict:
    """通过 GitHub API 创建仓库"""
    import requests
    import urllib3
    # 禁用 SSL 警告（如果使用代理可能会需要）
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description or "Auto pushed by Agent",
        "private": private,
        "auto_init": False
    }

    try:
        response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=30, verify=False)
    except requests.exceptions.SSLError as e:
        return {"success": False, "error": f"SSL 错误，请检查代理配置: {e}"}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": f"连接失败，请检查网络或代理: {e}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时，请检查网络或代理"}

    if response.status_code == 201:
        print(f"  ✅ 仓库创建成功")
        return {"success": True}
    elif response.status_code == 422:
        print(f"  ⚠️  仓库已存在，将覆盖推送")
        return {"success": True}
    else:
        return {
            "success": False,
            "error": f"创建仓库失败: {response.status_code} - {response.text}"
        }


def push_to_github(target_dir: str, repo_name: str, description: str, private: bool) -> dict:
    """
    将指定目录推送到GitHub

    Args:
        target_dir: 要推送的目录路径
        repo_name: GitHub仓库名
        description: 仓库描述
        private: 是否私有仓库

    Returns:
        推送结果
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"success": False, "error": "未配置 GITHUB_TOKEN，请在 .env 文件中设置"}

    github_user = os.environ.get("GITHUB_USER")
    if not github_user:
        return {"success": False, "error": "未配置 GITHUB_USER，请在 .env 文件中设置"}

    target_path = Path(target_dir).resolve()
    if not target_path.exists():
        return {"success": False, "error": f"目录不存在: {target_dir}"}

    proxy = get_proxy()
    proxies = {"https": proxy, "http": proxy} if proxy else {}

    print(f"\n{'='*60}")
    print(f"[GitHub推送]")
    print(f"  目录: {target_path}")
    print(f"  用户: {github_user}")
    print(f"  仓库: {repo_name}")
    print(f"  私有: {private}")
    print(f"  描述: {description}")
    if proxy:
        print(f"  代理: {proxy}")
    else:
        print(f"  代理: 未配置（如需代理请设置 HTTPS_PROXY 或 .env 中的 PROXY）")
    print(f"{'='*60}")

    # 步骤1：创建仓库
    print(f"\n[1/4] 创建远程仓库...")
    result = create_github_repo(token, github_user, repo_name, description, private, proxies)
    if not result["success"]:
        return result

    # 步骤2：初始化 git（如果还没有的话）
    git_dir = target_path / ".git"
    cwd = str(target_path)

    if not git_dir.exists():
        print(f"\n[2/4] 初始化 git 仓库...")
        r = run_cmd("git init", cwd)
        if not r["success"]:
            return {"success": False, "error": f"git init 失败: {r['stderr']}"}
    else:
        print(f"\n[2/4] git 仓库已存在，跳过初始化")

    # 配置 git 代理
    if proxy:
        print(f"  配置 git 代理...")
        run_cmd(f'git config http.proxy "{proxy}"', cwd)
        run_cmd(f'git config https.proxy "{proxy}"', cwd)

    # 步骤3：提交代码
    print(f"\n[3/4] 提交代码...")
    run_cmd("git add .", cwd)
    r = run_cmd('git diff --cached --quiet', cwd)
    if r["success"]:
        print(f"  ℹ️  没有新的更改需要提交")
    else:
        r = run_cmd('git commit -m "Auto pushed by Agent"', cwd)
        if not r["success"]:
            return {"success": False, "error": f"git commit 失败: {r['stderr']}"}
        print(f"  ✅ 提交成功")

    # 步骤4：推送到远程
    print(f"\n[4/4] 推送到 GitHub...")
    remote_url = f"https://{token}@github.com/{github_user}/{repo_name}.git"
    run_cmd("git remote remove origin", cwd)
    r = run_cmd(f"git remote add origin {remote_url}", cwd)
    if not r["success"]:
        return {"success": False, "error": f"添加远程仓库失败: {r['stderr']}"}

    run_cmd("git branch -M main", cwd)
    r = run_cmd("git push -u origin main --force", cwd, timeout=300)

    if r["success"]:
        repo_url = f"https://github.com/{github_user}/{repo_name}"
        print(f"\n{'='*60}")
        print(f"✅ 推送成功！")
        print(f"  仓库地址: {repo_url}")
        print(f"{'='*60}")
        return {"success": True, "repo_url": repo_url}
    else:
        return {"success": False, "error": f"git push 失败: {r['stderr']}"}


def main():
    parser = argparse.ArgumentParser(
        description="将指定目录的代码推送到 GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 推送 output_1 目录，自动命名为 output_1
  python push_to_github.py work/output_1

  # 指定仓库名
  python push_to_github.py work/output_1 --repo my-project

  # 私有仓库 + 描述
  python push_to_github.py work/output_1 --repo my-project --private --desc "我的项目"

  # 按序号推送（自动推断目录名和仓库名）
  python push_to_github.py --index 1

  # 推送序号 2，指定仓库名
  python push_to_github.py --index 2 --repo my-repo

代理配置（二选一）:
  # 方式1: 环境变量
  set HTTPS_PROXY=http://127.0.0.1:7890
  python push_to_github.py --index 1

  # 方式2: 在 .env 文件中添加
  PROXY=http://127.0.0.1:7890
"""
    )

    parser.add_argument(
        "directory",
        nargs="?",
        help="要推送的目录路径（如 work/output_1）"
    )
    parser.add_argument(
        "--index", "-i",
        type=int,
        help="按序号推送，自动推断为 work/output_N，仓库名默认为 output_N"
    )
    parser.add_argument(
        "--repo", "-r",
        help="GitHub 仓库名（不指定则使用目录名）"
    )
    parser.add_argument(
        "--desc", "-d",
        default="",
        help="仓库描述"
    )
    parser.add_argument(
        "--private", "-p",
        action="store_true",
        help="设为私有仓库（默认公开）"
    )
    parser.add_argument(
        "--work-dir", "-w",
        default="./work",
        help="工作目录（默认 ./work）"
    )
    parser.add_argument(
        "--proxy",
        help="代理地址（如 http://127.0.0.1:7890），优先级最高"
    )

    args = parser.parse_args()

    # 如果命令行指定了代理，设置到环境变量
    if args.proxy:
        os.environ["HTTPS_PROXY"] = args.proxy
        os.environ["HTTP_PROXY"] = args.proxy

    # 确定目录和仓库名
    if args.index is not None:
        target_dir = os.path.join(args.work_dir, f"output_{args.index}")
        default_repo = f"output_{args.index}"
    elif args.directory:
        target_dir = args.directory
        default_repo = Path(args.directory).name
    else:
        parser.error("请指定目录路径或使用 --index 参数")

    repo_name = args.repo or default_repo

    # 检查目录
    if not Path(target_dir).exists():
        print(f"❌ 目录不存在: {target_dir}")
        sys.exit(1)

    # 执行推送
    result = push_to_github(target_dir, repo_name, args.desc, args.private)

    if not result["success"]:
        print(f"\n❌ 推送失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
