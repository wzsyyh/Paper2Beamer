# Paper-to-Beamer

A tool that automatically converts academic papers in PDF format to Beamer presentation slides.

[中文版](../README.md)

## Project Introduction

Paper-to-Beamer is an AI-based tool that automatically converts academic papers in PDF format to Beamer presentation slides. It uses large language models to analyze paper content, extract key information, and generate well-structured presentations. The tool supports multi-turn dialogue modifications, allowing users to continuously optimize the generated slides through natural language feedback.

### Main Features

- **PDF content extraction**: Automatically extracts text, images, and structure from PDFs (based on the maker-pdf deep learning model)
- **Intelligent content analysis**: Identifies paper title, authors, abstract, section structure, and key figures
- **Presentation plan generation**: Generates a structured presentation plan based on paper content
- **Beamer code generation**: Generates complete LaTeX Beamer code
- **Multi-turn dialogue modification**: Supports modifying generated slides via natural language feedback
- **Multiple theme support**: Supports various Beamer themes
- **Chinese and English support**: Supports generating presentations in both Chinese and English

## Installation Guide

### Requirements

- Python 3.8+
- LaTeX environment (TeX Live or MiKTeX recommended)
- OpenAI API key

### Installation Steps

1. Clone the repository

```bash
git clone https://github.com/wzsyyh/paper-to-beamer.git
cd paper-to-beamer
```

2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Download the maker-pdf model (must be done before first use!)

```bash
pip install modelscope
python down_model.py
```
> The content of `down_model.py` is as follows:
> ```python
> from modelscope import snapshot_download
> snapshot_download('Lixiang/marker-pdf', local_dir='models')
> ```

5. Set the OpenAI API key

Create a `.env` file and add the following content:

```
OPENAI_API_KEY=your_api_key_here
```

Or set it in environment variables:

```bash
export OPENAI_API_KEY=your_api_key_here  # Linux/Mac
# or
set OPENAI_API_KEY=your_api_key_here  # Windows
```

> **Security Warning**: Never commit `.env` or `env.local` files containing real API keys to public repositories! These files are set to be ignored in `.gitignore`.

## Usage

### Web Interface

1. Start the web server

```bash
python app.py
```

2. Open http://localhost:7860 in your browser

3. Upload a PDF file, select language and theme, click the "Generate Presentation" button

4. Wait for processing to complete, download the generated PDF file

5. For modifications, enter your feedback in the "Provide Modification Suggestions" input box and submit

### Command Line

Basic usage:

```bash
python main.py path/to/your/paper.pdf
```

Advanced options:

```bash
python main.py path/to/your/paper.pdf --language en --model gpt-4o --theme Madrid --output-dir output
```

Interactive mode:

```bash
python main.py path/to/your/paper.pdf --interactive
```

Revision mode:

```bash
python main.py --revise --original-plan=path/to/plan.json --previous-tex=path/to/output.tex --feedback="Your modification suggestions"
```

Test mode:

```bash
python app.py --test path/to/paper.pdf --revise "Please modify the title page to center the title"
```

## Path conventions
- **All images are only saved in** `output/images/<session_id>/`, and all plan/tex image paths are standardized as `output/images/<session_id>/<filename>`. All subsequent steps reference this directory directly.

## FAQ
- **Figures not extracted or missing?**
  - Make sure you have downloaded the maker-pdf model and that images exist in `output/images/<session_id>/`.
- **API key not set?**
  - Add `OPENAI_API_KEY` to your `.env` file.

## For Developers

If you want to do secondary development, please refer to the [codebase documentation](../CODEBASE.md).

## License

This project is licensed under the MIT License. Secondary development must reference this repository. Secondary development for commercial purposes requires contacting the original author for authorization.

## Contact

For issues or suggestions, please:

- Submit GitHub Issues
- Send emails to: yangyuheng@westlake.edu.cn 