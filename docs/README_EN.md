# Paper-to-Beamer

A tool that automatically converts academic papers in PDF format to Beamer presentation slides

[中文版](../README.md)

## Project Introduction

Paper-to-Beamer is an AI-based tool that automatically converts academic papers in PDF format to Beamer presentation slides. It uses large language models to analyze paper content, extract key information, and generate well-structured presentations. The tool supports multi-turn dialogue modifications, allowing users to continuously optimize the generated slides through natural language feedback.

### Main Features

- **PDF Content Extraction**: Automatically extract text, images, and structural information from PDFs
- **Intelligent Content Analysis**: Identify paper titles, authors, abstracts, section structures, and key figures
- **Presentation Plan Generation**: Generate structured presentation plans based on paper content
- **Beamer Code Generation**: Generate complete LaTeX Beamer code
- **Multi-turn Dialogue Modifications**: Support modifying generated slides through natural language feedback
- **Multiple Theme Support**: Support various Beamer themes
- **Multilingual Support**: Support generating presentations in both Chinese and English

## Installation Guide

### Requirements

- Python 3.8+
- LaTeX environment (TeX Live or MiKTeX recommended)
- OpenAI API key

### Installation Steps

1. Clone the repository

```bash
git clone https://github.com/yourusername/paper-to-beamer.git
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

4. Set up OpenAI API key

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

## Common Issues

### 1. Compilation Failure

If you encounter compilation failures, please check:
- Whether a complete LaTeX environment is installed
- Whether Chinese fonts are installed (if generating Chinese presentations)
- Whether there is enough disk space

### 2. Image Display Issues

If images are not displaying correctly:
- Ensure the image quality in the PDF is good enough
- Try using different Beamer themes

### 3. API Key Issues

If you encounter API key-related errors:
- Ensure the API key is set correctly
- Check if the API key has sufficient quota

## Secondary Development

If you want to do secondary development, please refer to the [codebase documentation](../CODEBASE.md).

## License

This project is licensed under the MIT License. Secondary development must reference this repository. Secondary development for commercial purposes requires contacting the original author for authorization.

## Contact

If you have any questions or suggestions, please contact through:

- Submit GitHub Issues
- Send emails to: your.email@example.com 

> **Security Warning**: Never commit `.env` or `env.local` files containing real API keys to public repositories! These files are set to be ignored in `.gitignore`. 