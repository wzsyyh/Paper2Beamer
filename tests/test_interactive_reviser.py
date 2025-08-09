import os
import sys
import logging
from pathlib import Path

# 将项目根目录添加到Python路径，以确保可以正确导入模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from modules.interactive_reviser import EditorAgent

def setup_logging(verbose=True):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def main():
    """
    交互式测试EditorAgent的主函数
    """
    logger = setup_logging()

    # 加载环境变量 (OPENAI_API_KEY, OPENAI_API_BASE)
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("错误：未找到 OPENAI_API_KEY 环境变量。请在 .env 文件中设置。")
        return

    # --- 配置测试文件 ---
    # 您可以修改这些路径来测试不同的案例
    SESSION_ID = "1754661367"
    BASE_OUTPUT_DIR = project_root / "output"
    
    plan_path = BASE_OUTPUT_DIR / "plan" / SESSION_ID / "lightweight_presentation_plan.json"
    tex_dir = BASE_OUTPUT_DIR / "tex" / SESSION_ID
    initial_tex_path = tex_dir / "output.tex"

    if not plan_path.exists() or not initial_tex_path.exists():
        logger.error(f"错误：测试文件未找到。请确保路径正确：")
        logger.error(f"Plan: {plan_path}")
        logger.error(f"TeX: {initial_tex_path}")
        return

    # --- 初始化Agent ---
    # 您可以修改使用的模型
    MODEL_NAME = "gpt-4o"
    editor_agent = EditorAgent(model_name=MODEL_NAME)

    logger.info("="*50)
    logger.info("欢迎来到 Editor Agent 交互式测试环境！")
    logger.info(f"将要修改的初始TEX文件: {initial_tex_path}")
    logger.info("="*50)

    current_tex_path = str(initial_tex_path)
    revision_count = 1

    while True:
        try:
            user_feedback = input(f"\n[第 {revision_count} 轮修订] 请输入您的修改建议 (或输入 'exit' 退出): ")
            if user_feedback.lower() in ['exit', 'quit', '退出']:
                logger.info("感谢使用，退出测试环境。")
                break

            if not user_feedback.strip():
                logger.warning("输入为空，请重新输入。")
                continue

            # 调用Agent进行修订
            # 注意：当前revise方法还不包含编译步骤
            success, new_path, message = editor_agent.revise(
                user_feedback=user_feedback,
                tex_path=current_tex_path,
                plan_path=str(plan_path),
                output_dir=str(tex_dir)
            )

            if success:
                logger.info(f"✅ 修订成功！")
                logger.info(f"新的TEX文件已保存至: {new_path}")
                logger.info("请检查文件内容是否符合预期。")
                # 更新当前TEX文件路径，为下一次迭代做准备
                current_tex_path = new_path
                revision_count += 1
            else:
                logger.error(f"❌ 修订失败: {message}")
                logger.info("当前TEX文件未改变。您可以根据错误信息调整您的反馈，然后重试。")

        except (KeyboardInterrupt, EOFError):
            logger.info("\n用户中断。退出测试环境。")
            break
        except Exception as e:
            logger.error(f"发生未知错误: {e}", exc_info=True)
            break

if __name__ == "__main__":
    main()
