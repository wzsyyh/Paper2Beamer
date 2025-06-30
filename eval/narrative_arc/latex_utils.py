import re

def extract_frames(tex_content):
    """
    Extracts the content of each frame from a LaTeX string.
    A frame is defined by \begin{frame}...\end{frame}.
    This function returns a list of strings, where each string is the content of a frame.
    """
    # This regex finds all content between \begin{frame} and \end{frame}
    # It uses re.DOTALL to make '.' match newlines.
    # It is non-greedy (.*?) to handle multiple frames correctly.
    frames = re.findall(r'\\begin{frame}(.*?)\\end{frame}', tex_content, re.DOTALL)
    
    cleaned_frames = []
    for frame in frames:
        # Extract frame title if it exists
        title_match = re.search(r'\\frametitle\{(.*?)\}', frame)
        title = title_match.group(1) if title_match else ""
        
        # A simple approach to remove some common LaTeX commands for cleaner text
        content = re.sub(r'\\[a-zA-Z]+(\[.*?\])?(\{.*?\})?', '', frame)
        content = content.replace('\n', ' ').replace('  ', ' ').strip()
        
        cleaned_frames.append({"title": title, "content": content})
        
    return cleaned_frames
