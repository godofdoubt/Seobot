# analyzer/run_llm_analysis_end_class.py
import asyncio
import os
import sys
import logging
# Ensure the analyzer directory is in PYTHONPATH if running from elsewhere,
# or rely on the script being in the same directory as llm_analysis_end_processor.py
try:
    from llm_analysis_end_processor import LLMAnalysisEndProcessor
except ImportError:
    # This fallback might be needed if script is run with CWD not being project root
    # and 'analyzer' is not in sys.path. Better to ensure PYTHONPATH includes 'analyzer' parent dir.
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from llm_analysis_end_processor import LLMAnalysisEndProcessor


# Configure basic logging for the runner script itself
# This will be configured by the LLMAnalysisEndProcessor's __init__ as well,
# but setting a basic one here helps catch early runner issues.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - RUNNER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main_runner():
    try:
        processor = LLMAnalysisEndProcessor()
    except ValueError as e:
        logger.critical(f"Failed to initialize LLMAnalysisEndProcessor: {e}. Check environment variables.")
        sys.exit(1)
    except RuntimeError as e:
        logger.critical(f"Runtime error during LLMAnalysisEndProcessor initialization: {e}.")
        sys.exit(1)


    report_ids_to_process = []
    process_pending_flag = False

    if len(sys.argv) > 1:
        # Assume all arguments after the script name are report IDs
        report_ids_to_process = sys.argv[1:]
        logger.info(f"Runner: Received request to process specific report IDs: {report_ids_to_process}")
    else:
        process_pending_flag = True
        logger.info(f"Runner: No specific report IDs provided. Will process pending reports.")
    
    batch_size_env = os.getenv('PROCESS_BATCH_SIZE', '10')
    try:
        batch_size = int(batch_size_env)
    except ValueError:
        logger.warning(f"Invalid PROCESS_BATCH_SIZE '{batch_size_env}'. Defaulting to 10.")
        batch_size = 10

    if report_ids_to_process:
        await processor.run(report_ids=report_ids_to_process)
    elif process_pending_flag:
        await processor.run(process_pending=True, batch_size=batch_size)
    else:
        # This case should ideally not be reached if logic above is correct
        logger.info("Runner: No action specified (no report IDs, not flagged for pending). Processing pending by default.")
        await processor.run(process_pending=True, batch_size=batch_size)

    logger.info("Runner: Finished all processing tasks.")

if __name__ == "__main__":
    try:
        asyncio.run(main_runner())
    except Exception as e:
        logger.critical(f"Critical unhandled error in runner's main_runner: {e}", exc_info=True)
        sys.exit(1)