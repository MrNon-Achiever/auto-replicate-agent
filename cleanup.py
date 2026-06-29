"""
清理脚本 - 清理work目录
支持清理特定序号的仓库或整个目录
"""

import os
import shutil
import stat
import sys
from pathlib import Path


def cleanup_work_dir(work_dir: str = "./work"):
    """
    清理work目录

    Args:
        work_dir: 要清理的目录
    """
    work_path = Path(work_dir)

    if not work_path.exists():
        print(f"目录不存在: {work_dir}")
        return

    print(f"正在清理目录: {work_dir}")

    try:
        # Windows上删除.git目录可能需要特殊处理
        def remove_readonly(func, path, excinfo):
            """处理只读文件"""
            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(work_path, onerror=remove_readonly)
        print("✅ 清理完成")
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        print("请手动删除该目录")
        sys.exit(1)


def cleanup_by_index(work_dir: str, index: int):
    """
    清理特定序号的仓库

    Args:
        work_dir: 工作目录
        index: 仓库序号
    """
    work_path = Path(work_dir)

    target_dir = work_path / f"target_repo_{index}"
    output_dir = work_path / f"output_{index}"

    dirs_to_clean = []

    if target_dir.exists():
        dirs_to_clean.append(target_dir)
    if output_dir.exists():
        dirs_to_clean.append(output_dir)

    if not dirs_to_clean:
        print(f"未找到序号为 {index} 的仓库目录")
        return

    print(f"将清理以下目录：")
    for d in dirs_to_clean:
        print(f"  - {d}")

    try:
        def remove_readonly(func, path, excinfo):
            """处理只读文件"""
            os.chmod(path, stat.S_IWRITE)
            func(path)

        for d in dirs_to_clean:
            shutil.rmtree(d, onerror=remove_readonly)
            print(f"✅ 已清理: {d.name}")

        print("✅ 清理完成")
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        print("请手动删除相关目录")
        sys.exit(1)


def list_repos(work_dir: str):
    """
    列出所有已克隆的仓库

    Args:
        work_dir: 工作目录
    """
    work_path = Path(work_dir)

    if not work_path.exists():
        print(f"目录不存在: {work_dir}")
        return

    repos = []
    for item in work_path.iterdir():
        if item.is_dir() and item.name.startswith("target_repo_"):
            try:
                index = int(item.name.split("_")[-1])
                output_dir = work_path / f"output_{index}"
                repos.append({
                    "index": index,
                    "target": item,
                    "output": output_dir if output_dir.exists() else None
                })
            except ValueError:
                pass

    if not repos:
        print("未找到任何已克隆的仓库")
        return

    print("已克隆的仓库：")
    for repo in sorted(repos, key=lambda x: x["index"]):
        print(f"  序号 {repo['index']}:")
        print(f"    目标仓库: {repo['target'].name}")
        if repo["output"]:
            print(f"    输出目录: {repo['output'].name}")
        else:
            print(f"    输出目录: 未生成")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="清理work目录")
    parser.add_argument(
        "--work-dir",
        default="./work",
        help="要清理的目录 (默认: ./work)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制清理，不询问确认"
    )
    parser.add_argument(
        "--index",
        type=int,
        help="清理特定序号的仓库（如: --index 1 清理 target_repo_1 和 output_1）"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有已克隆的仓库"
    )

    args = parser.parse_args()

    # 列出仓库
    if args.list:
        list_repos(args.work_dir)
        return

    work_path = Path(args.work_dir)

    if not work_path.exists():
        print(f"目录不存在: {args.work_dir}")
        return

    # 清理特定序号
    if args.index is not None:
        if not args.force:
            confirm = input(f"确定要清理序号为 {args.index} 的仓库吗？(y/N): ")
            if confirm.lower() != 'y':
                print("取消清理")
                return
        cleanup_by_index(args.work_dir, args.index)
        return

    # 清理整个目录
    # 显示目录大小
    total_size = sum(f.stat().st_size for f in work_path.rglob('*') if f.is_file())
    file_count = sum(1 for f in work_path.rglob('*') if f.is_file())

    print(f"目录: {args.work_dir}")
    print(f"文件数: {file_count}")
    print(f"总大小: {total_size / 1024 / 1024:.2f} MB")

    if not args.force:
        confirm = input("\n确定要清理该目录吗？(y/N): ")
        if confirm.lower() != 'y':
            print("取消清理")
            return

    cleanup_work_dir(args.work_dir)


if __name__ == "__main__":
    main()
