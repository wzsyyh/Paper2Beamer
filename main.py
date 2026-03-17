#!/usr/bin/env python3
"""
Paper to Beamer Conversion Tool - Main Program
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Load patches
from patch_openai import patch_openai_client, patch_langchain_openai

# Load environment variables
from dotenv import load_dotenv
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# Apply patches
patch_openai_client()
patch_langchain_openai()

# Import modules
from modules.pdf_parser import extract_pdf_content
from modules.presentation_planner import generate_presentation_plan
from modules.tex_workflow import run_tex_workflow, run_revision_tex_workflow
from modules.workflow_state import WorkflowState

def setup_logging(verbose=False):
    """Set up logging level and format"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Convert academic paper PDF to Beamer presentation'
    )
    
    # Required arguments
    parser.add_argument(
        'pdf_path', 
        help='Input PDF file path'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output-dir', '-o',
        default='output',
        help='Output directory'
    )
    parser.add_argument(
        '--language', '-l',
        choices=['zh', 'en'],
        default='en',
        help='Output language, zh for Chinese, en for English'
    )
    parser.add_argument(
        '--model', '-m',
        default=os.environ.get('MODEL_NAME', 'gpt-4o'),
        help='Language model to use (default: from MODEL_NAME env var or gpt-4o)'
    )
    parser.add_argument(
        '--max-retries', '-r',
        type=int,
        default=5,
        help='Maximum retries when compilation fails'
    )
    parser.add_argument(
        '--skip-compilation', '-s',
        action='store_true',
        default=True,
        help='Skip PDF compilation (generate TEX only)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose logs'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Enable interactive mode, allow users to optimize presentation plan through multi-turn dialogue'
    )
    # Add support for revision mode
    parser.add_argument(
        '--revise', '-R',
        action='store_true',
        help='Enable revision mode, allow users to provide feedback to modify generated presentations'
    )
    parser.add_argument(
        '--original-plan', 
        help='Original presentation plan JSON file path (used in revision mode)'
    )
    parser.add_argument(
        '--previous-tex', 
        help='Previous version TEX file path (used in revision mode)'
    )
    parser.add_argument(
        '--feedback', 
        help='User feedback content (used in revision mode)'
    )
    parser.add_argument(
        '--theme',
        default='Madrid',
        help='Beamer theme, such as Madrid, Berlin, Singapore, etc.'
    )
    parser.add_argument(
        '--disable-llm-enhancement',
        action='store_true',
        help='Disable LLM enhancement, use basic PDF parsing only'
    )
    parser.add_argument(
        '--no-interactive-revise',
        action='store_true',
        help='Disable ReAct mode interactive revision (enabled by default)'
    )
    parser.add_argument(
        '--enable-verification',
        action='store_true',
        default=True,
        help='Enable presentation plan verification agent (detect consistency and hallucination) [enabled by default]'
    )
    parser.add_argument(
        '--enable-auto-repair',
        action='store_true',
        default=True,
        help='Enable auto-repair agent (automatically fix issues based on verification results) [enabled by default]'
    )
    parser.add_argument(
        '--disable-verification',
        action='store_true',
        help='Disable verification and repair functions (fast mode)'
    )
    parser.add_argument(
        '--enable-speech',
        action='store_true',
        help='Enable speech generation agent (generate accompanying speech script)'
    )
    parser.add_argument(
        '--speech-duration',
        type=int,
        default=15,
        help='Target speech duration (minutes, default 15 minutes)'
    )
    parser.add_argument(
        '--speech-style',
        choices=['academic_conference', 'classroom', 'industry_presentation', 'public_talk'],
        default='academic_conference',
        help='Speech style type'
    )
    
    return parser.parse_args()

def interactive_dialog(planner, logger):
    """
    Interactive dialog with user to optimize presentation plan
    
    Args:
        planner: Presentation plan generator instance
        logger: Logger instance
        
    Returns:
        Dict: Optimized presentation plan
    """
    logger.info("Entering interactive mode. Enter feedback to improve plan. Type 'exit' to quit.")
    
    while True:
        user_input = input("\nEnter your feedback: ")
        
        # Check for exit
        if user_input.lower() in ['exit', 'quit']:
            logger.info("Exiting interactive mode")
            break
            
        # Process user input
        logger.info("Processing feedback...")
        response, updated_plan = planner.continue_conversation(user_input)
        
        # Print model response
        print("\n==== Model Response ====")
        print(response)
        print("========================")
        
    return planner.presentation_plan

def main():
    """Main function"""
    # Parse command line arguments
    args = parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return 1
    
    # Create output directory
    output_dir = args.output_dir
    
    # Use unique session ID to distinguish different runs
    from datetime import datetime
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output directories for each stage
    raw_dir = os.path.join(output_dir, "raw", session_id)
    plan_dir = os.path.join(output_dir, "plan", session_id)
    tex_dir = os.path.join(output_dir, "tex", session_id)
    img_dir = os.path.join(output_dir, "images", session_id)
    
    for dir_path in [raw_dir, plan_dir, tex_dir, img_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Create workflow state manager
    workflow_state = WorkflowState(
        session_id=session_id,
        original_pdf_path=args.pdf_path,
        output_base_dir=output_dir
    )
    
    # Check if in revision mode
    if args.revise:
        # Validate required parameters for revision mode
        if not args.original_plan or not args.previous_tex or not args.feedback:
            logger.error("Revision mode requires --original-plan, --previous-tex and --feedback parameters")
            return 1
            
        # Check if files exist
        if not os.path.exists(args.original_plan):
            logger.error(f"Original presentation plan file does not exist: {args.original_plan}")
            return 1
            
        if not os.path.exists(args.previous_tex):
            logger.error(f"Previous version TEX file does not exist: {args.previous_tex}")
            return 1
            
        # Run revision TEX workflow
        logger.info("Starting revision mode...")
        
        success, message, pdf_path = run_revision_tex_workflow(
            original_plan_path=args.original_plan,
            previous_tex_path=args.previous_tex,
            user_feedback=args.feedback,
            output_dir=tex_dir,
            model_name=args.model,
            language=args.language,
            theme=args.theme,
            max_retries=args.max_retries
        )
        
        if success:
            logger.info(f"Revision TEX generation and compilation successful: {message}")
            logger.info(f"Generated PDF file: {pdf_path}")
            return 0
        else:
            logger.error(f"Revision TEX generation and compilation failed: {message}")
            return 1
    
    # Original logic for non-revision mode
    # Check input file
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF file does not exist: {args.pdf_path}")
        return 1
        
    # Step 1: Extract PDF content
    logger.info("Step 1: Extracting PDF content...")
    try:
        # Decide whether to enable LLM enhancement
        enable_llm_enhancement = not args.disable_llm_enhancement and bool(api_key)
        
        if not enable_llm_enhancement:
            if args.disable_llm_enhancement:
                logger.info("User disabled LLM enhancement feature")
            else:
                logger.warning("API key not set, LLM enhancement will be disabled")
        
        pdf_content, raw_content_path, actual_img_dir = extract_pdf_content(
            pdf_path=args.pdf_path, 
            output_dir=raw_dir,
            enable_llm_enhancement=enable_llm_enhancement,
            model_name=args.model,
            api_key=api_key
        )
        if not pdf_content:
            logger.error("PDF content extraction failed")
            return 1
            
        logger.info(f"PDF content saved to: {raw_content_path}")
        logger.info(f"Images saved to: {actual_img_dir}")
        
        # Update workflow state - use actual image directory
        workflow_state.set_parser_output(raw_content_path)
        workflow_state.images_dir = actual_img_dir
        
        # Check if LLM enhancement was successfully used
        if pdf_content.get("enhanced_content"):
            logger.info("✅ LLM enhanced content extraction successful")
            enhanced = pdf_content["enhanced_content"]
            logger.info(f"Extracted {len(enhanced.get('tables', []))} tables")
            logger.info(f"Extracted {len(enhanced.get('presentation_sections', {}))} presentation sections")
        else:
            logger.info("Using basic PDF parsing (LLM enhancement not enabled)")
    except Exception as e:
        logger.error(f"PDF content extraction failed: {str(e)}")
        return 1
            
    # Step 2: Generate presentation plan
    logger.info("Step 2: Generating presentation plan...")
    try:
        presentation_plan, plan_path, planner = generate_presentation_plan(
            raw_content_path=raw_content_path,
            output_dir=plan_dir,
            model_name=args.model,
            language=args.language
        )
            
        if not presentation_plan:
            logger.error("Presentation plan generation failed")
            return 1
            
        logger.info(f"Presentation plan saved to: {plan_path}")
        
        # Update workflow state
        workflow_state.set_planner_output(plan_path)
            
        # If interactive mode is enabled, enter dialog
        if args.interactive and planner:
            logger.info("Starting interactive optimization...")
            presentation_plan = interactive_dialog(planner, logger)
            
            # Save optimized plan
            plan_path = planner.save_presentation_plan(presentation_plan)
            logger.info(f"Optimized presentation plan saved to: {plan_path}")
            
            # Update workflow state
            workflow_state.set_planner_output(plan_path)
    except Exception as e:
        logger.error(f"Presentation plan generation failed: {str(e)}")
        return 1
    
    # Step 2.5: Verify presentation plan (using simplified verification agent)
    verification_passed = True
    verification_report = None
    verification_report_path = None
    if args.enable_verification and not args.disable_verification:
        verification_dir = os.path.join(output_dir, "verification", session_id)
        os.makedirs(verification_dir, exist_ok=True)
        
        try:
            # Import simplified verification agent
            from modules.simplified_verification_agent import verify_content_coverage
            
            logger.info("Step 2.5: Verifying content coverage...")
            logger.info("Checking if core content is adequately covered...")
            
            verification_passed, verification_report, verification_report_path = verify_content_coverage(
                original_content_path=raw_content_path,
                presentation_plan_path=plan_path,
                output_dir=verification_dir,
                model_name=args.model,
                language=args.language
            )
            
            # Update workflow state
            workflow_state.set_verification_output(verification_report_path, verification_passed)
            
            if verification_passed:
                logger.info("✅ Content coverage verification passed")
                if verification_report_path:
                    logger.info(f"Verification report saved to: {verification_report_path}")
            else:
                logger.warning("⚠️ Insufficient content coverage, repair recommended")
                if verification_report_path:
                    logger.warning(f"Verification report saved to: {verification_report_path}")
                
                # Display missing content summary
                if verification_report and "missing_content" in verification_report:
                    missing_content = verification_report["missing_content"]
                    if missing_content:
                        logger.warning("Missing important content:")
                        for item in missing_content[:3]:  # Only show first 3
                            logger.warning(f"  - {item.get('area', 'Unknown')}: {item.get('missing_content', '')[:100]}...")
                
                # For insufficient content coverage, ask user whether to continue
                if verification_report and verification_report.get("missing_content"):
                    user_choice = input("\nInsufficient content coverage detected. Enable auto-repair? (y/n): ").strip().lower()
                    if user_choice != 'y':
                        logger.info("User chose to skip repair, continuing generation")
                        verification_passed = True  # Allow continuation
            
        except Exception as e:
            logger.warning(f"Verification step failed, continuing execution: {str(e)}")
            # Verification failure does not affect main process continuation
            verification_passed = True  # Set to True to avoid blocking process
    
    # Step 2.6: Auto-repair (using simplified repair agent)
    repaired_plan_path = plan_path  # Default to original plan
    if args.enable_auto_repair and not args.disable_verification and args.enable_verification and verification_report and not verification_passed:
        repair_dir = os.path.join(output_dir, "repair", session_id)
        os.makedirs(repair_dir, exist_ok=True)
        
        try:
            # Import simplified repair agent
            from modules.simplified_repair_agent import repair_content_coverage
            
            logger.info("Step 2.6: Supplementing missing content...")
            logger.info("Supplementing important content based on verification results...")
            
            repair_success, repair_report, repaired_plan_path = repair_content_coverage(
                presentation_plan_path=plan_path,
                verification_report_path=verification_report_path,
                original_content_path=raw_content_path,
                output_dir=repair_dir,
                model_name=args.model,
                language=args.language
            )
            
            if repair_success:
                logger.info("✅ Content supplementation completed")
                logger.info(f"Supplemented plan saved to: {repaired_plan_path}")
                
                # Display repair summary
                if repair_report and "repair_summary" in repair_report:
                    summary = repair_report["repair_summary"]
                    total_repairs = summary.get('total_repairs', 0)
                    logger.info(f"Number of supplemented content: {total_repairs}")
                    if total_repairs > 0:
                        logger.info("Content coverage has been improved")
                
                # Update workflow state to use repaired plan
                workflow_state.set_planner_output(repaired_plan_path)
                plan_path = repaired_plan_path  # Update variable for subsequent TEX generation
            else:
                logger.info("⚠️ No content requiring supplementation found, or supplementation failed")
                logger.info("Will continue using original presentation plan")
            
        except Exception as e:
            logger.warning(f"Auto-repair step failed, continuing execution: {str(e)}")
            # Repair failure does not affect main process continuation
        
    # Step 3: Generate TEX and speech script in parallel
    logger.info("Step 3: Generating and compiling TEX...")
    
    # 3.1: TEX generation and compilation
    try:
        success, message, pdf_path = run_tex_workflow(
            presentation_plan_path=plan_path,
            output_dir=tex_dir,
            model_name=args.model,
            language=args.language,
            theme=args.theme,
            max_retries=args.max_retries,
            skip_compilation=args.skip_compilation  # Only skip compilation, not TEX generation
        )
        
        if success:
            logger.info(f"TEX generation and compilation successful: {message}")
            logger.info(f"Generated PDF file: {pdf_path}")
            
            # Update workflow state
            tex_files = [f for f in os.listdir(tex_dir) if f.endswith(".tex") and not f.endswith("_revised.tex")]
            if tex_files:
                tex_file_path = os.path.join(tex_dir, tex_files[0])
                workflow_state.set_tex_output(tex_file_path, pdf_path)
        
        # 3.2: Speech script generation (optional, parallel with TEX generation)
        speech_success = False
        speech_path = None
        if args.enable_speech:
            try:
                # Import speech script generation agent
                from modules.speech_generator import generate_speech_for_presentation
                
                logger.info("Step 3.2: Generating speech script...")
                
                speech_dir = os.path.join(output_dir, "speech", session_id)
                os.makedirs(speech_dir, exist_ok=True)
                
                speech_success, speech_result, speech_path = generate_speech_for_presentation(
                    presentation_plan_path=plan_path,
                    output_dir=speech_dir,
                    original_content_path=raw_content_path,
                    target_duration_minutes=args.speech_duration,
                    presentation_style=args.speech_style,
                    audience_level="expert",
                    model_name=args.model
                )
                
                if speech_success:
                    logger.info("✅ Speech script generation successful")
                    logger.info(f"Speech script saved to: {speech_path}")
                    
                    if speech_result and "speech_summary" in speech_result:
                        summary = speech_result["speech_summary"]
                        logger.info(f"Speech duration: {summary.get('estimated_duration', 'N/A')} minutes")
                        logger.info(f"Number of slides: {summary.get('total_slides', 'N/A')}")
                        logger.info(f"Presentation style: {summary.get('presentation_style', 'N/A')}")
                    
                    # Update workflow state
                    workflow_state.set_speech_output(speech_path, speech_success)
                else:
                    logger.warning("⚠️ Speech script generation failed")
                    
            except Exception as e:
                logger.warning(f"Speech script generation step failed: {str(e)}")
                # Speech script generation failure does not affect main process
                
        if success:
            
            # Enable interactive revision mode by default, unless user explicitly disables it
            if not args.no_interactive_revise:
                logger.info("\n=== Starting Interactive Revision Mode ===")
                logger.info("PDF has been generated. You can now modify slide content through natural language dialogue.")
                
                # Import and start new version ReAct mode interactive editor
                from modules.react_interactive_editor_new import ReactInteractiveEditor
                
                if workflow_state.tex_output_path:
                    logger.info(f"Will edit file: {workflow_state.tex_output_path}")
                    
                    # Start new version interactive editor, passing original PDF content and workflow state
                    # Extract original text from PDF content
                    source_text = None
                    if isinstance(pdf_content, dict) and 'full_text' in pdf_content:
                        source_text = pdf_content['full_text']
                    elif isinstance(pdf_content, str):
                        source_text = pdf_content
                    
                    editor = ReactInteractiveEditor(
                        workflow_state.tex_output_path, 
                        source_content=source_text,
                        workflow_state=workflow_state,
                        model_name=args.model
                    )
                    editor.interactive_session()
                else:
                    logger.error("Generated TEX file not found, cannot start interactive revision mode")
            
            # Output revision mode usage hints (if interactive revision is disabled)
            if args.no_interactive_revise:
                previous_tex_path = os.path.join(tex_dir, 'output.tex')
                if not os.path.exists(previous_tex_path):
                    # Try to find other tex files
                    tex_files = [f for f in os.listdir(tex_dir) if f.endswith(".tex")]
                    if tex_files:
                        previous_tex_path = os.path.join(tex_dir, tex_files[0])

                logger.info("\n=== Revision Options ===")
                logger.info("1. Command line revision mode:")
                logger.info(f"   python main.py --revise --original-plan='{plan_path}' --previous-tex='{previous_tex_path}' --feedback=\"Your modification suggestions\" --output-dir='{output_dir}' --theme={args.theme}")
                logger.info("2. Interactive revision mode (enable when re-running):")
                logger.info(f"   python main.py '{args.pdf_path}' --output-dir='{output_dir}' --theme={args.theme}")
            else:
                logger.info("\n💡 Tip: If you don't need interactive revision, you can use the --no-interactive-revise parameter to skip it.")
            
            # Output new feature hints
            print("\n🔧 New Feature Hints:")
            print("- ✅ Smart image matching algorithm enabled, more accurate image allocation")
            print("- ✅ Chart separation rules enabled, avoiding single page overload") 
            print("- ✅ Background section requirements strengthened, more complete presentation structure")
            
            return 0
        else:
            logger.error(f"TEX generation and compilation failed: {message}")
            return 1
    except Exception as e:
        logger.error(f"TEX workflow execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
