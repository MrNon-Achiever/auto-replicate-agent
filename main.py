"""
全自动复刻项目Agent - 主入口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from agent.core import CloneAgent
from agent import config


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="全自动复刻项目Agent")
    parser.add_argument("repo_url", help="要复刻的仓库URL")
    parser.add_argument("--work-dir", default=config.WORK_DIR, help="工作目录")

    args = parser.parse_args()

    # 创建智能体
    agent = CloneAgent(args.work_dir)

    # 设置回调函数
    def on_progress(message):
        print(f"\n{'='*50}")
        print(f"进度: {message}")
        print(f"{'='*50}\n")

    def on_error(error):
        print(f"\n{'='*50}")
        print(f"错误: {error}")
        print(f"{'='*50}\n")

    agent.on_progress = on_progress
    agent.on_error = on_error

    # 执行复刻
    print(f"\n开始复刻: {args.repo_url}")
    print(f"工作目录: {args.work_dir}\n")

    result = agent.clone_repo(args.repo_url)

    if result.get("success"):
        print("\n✅ 复刻成功！")
        print(f"输出目录: {result.get('output_dir')}")
        sys.exit(0)
    else:
        print(f"\n❌ 复刻失败: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
