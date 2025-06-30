import re
from typing import List, Dict

def clean_tex_content(content: str) -> str:
    """
    A simple utility to clean common LaTeX commands from a string for better LLM processing.
    """
    # Remove comments
    content = re.sub(r'%.*?\n', ' ', content)
    # Remove frame title and other sectioning commands
    content = re.sub(r'\\(frame|sub?section\*?|frametitle){.*?}', '', content, flags=re.DOTALL)
    # Remove labels
    content = re.sub(r'\\label{.*?}', '', content)
    # Replace itemize/enumerate with simple lists
    content = re.sub(r'\\item\s+', '- ', content)
    content = re.sub(r'\\begin{(itemize|enumerate|description)}', '', content)
    content = re.sub(r'\\end{(itemize|enumerate|description)}', '', content)
    # Remove figure environments
    content = re.sub(r'\\begin{figure}.*?\\end{figure}', '[FIGURE]', content, flags=re.DOTALL)
    # Remove \includegraphics
    content = re.sub(r'\\includegraphics.*?{.*?}', '[IMAGE]', content)
    # Remove dynamic overlays
    content = re.sub(r'\\pause\s*', '', content)
    # A generic catch-all for other simple commands, be careful with this one
    content = re.sub(r'\\[a-zA-Z]+', '', content)
    # Remove leftover curly braces
    content = re.sub(r'[{}]', '', content)
    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    return content

def extract_frames_from_tex(tex_content: str) -> List[Dict[str, str]]:
    """
    Parses a LaTeX string to extract the content of each frame.

    Args:
        tex_content: A string containing the LaTeX document.

    Returns:
        A list of dictionaries, where each dictionary represents a frame
        and contains its 'title' and 'content'.
    """
    frame_pattern = re.compile(r'\\begin{frame}(.*?)\\end{frame}', re.DOTALL)
    title_pattern = re.compile(r'\\frametitle{(.*?)}', re.DOTALL)

    frames = []
    for match in frame_pattern.finditer(tex_content):
        frame_block = match.group(1)
        
        title_match = title_pattern.search(frame_block)
        title = title_match.group(1).strip() if title_match else ""
        
        # Combine title and content for classification
        full_content = f"Title: {title}\n\nContent: {clean_tex_content(frame_block)}"
        
        frames.append({
            "title": title,
            "cleaned_content": full_content.strip()
        })
        
    return frames

def get_frames_from_file(file_path: str) -> List[Dict[str, str]]:
    """
    Reads a .tex file and extracts the content of each frame.

    Args:
        file_path: The path to the .tex file.

    Returns:
        A list of dictionaries representing the frames.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return extract_frames_from_tex(content)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except Exception as e:
        print(f"An error occurred while reading/parsing the file: {e}")
        return []
