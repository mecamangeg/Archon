# File: python/src/server/services/sync/chunker.py

from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class CodeChunk:
    """Represents a chunk of code"""
    content: str
    start_line: int
    end_line: int
    language: str
    section_type: Optional[str] = None  # 'class', 'function', 'module', etc.
    section_name: Optional[str] = None


class Chunker:
    """
    Chunks code files using language-aware boundaries.

    Strategies:
    - Python: Split by class/function definitions
    - TypeScript/JavaScript: Split by class/interface/function
    - Markdown: Split by headers
    - Generic: Split by line count with overlap
    """

    DEFAULT_CHUNK_SIZE = 100  # lines
    DEFAULT_OVERLAP = 10  # lines

    def chunk_file(
        self,
        content: str,
        language: str,
        max_lines: int = DEFAULT_CHUNK_SIZE,
        overlap_lines: int = DEFAULT_OVERLAP
    ) -> List[CodeChunk]:
        """
        Chunk file content based on language.

        Args:
            content: File content
            language: Programming language (python, typescript, markdown, etc.)
            max_lines: Maximum lines per chunk
            overlap_lines: Number of overlapping lines between chunks

        Returns:
            List of CodeChunk objects
        """
        if language == 'python':
            return self._chunk_python(content, max_lines, overlap_lines)
        elif language in ['typescript', 'javascript', 'tsx', 'jsx']:
            return self._chunk_typescript(content, max_lines, overlap_lines)
        elif language == 'markdown':
            return self._chunk_markdown(content, max_lines)
        else:
            return self._chunk_generic(content, max_lines, overlap_lines)

    def _chunk_python(
        self,
        content: str,
        max_lines: int,
        overlap_lines: int
    ) -> List[CodeChunk]:
        """
        Chunk Python code by class and function definitions.
        """
        lines = content.split('\n')
        chunks = []
        current_chunk_lines = []
        current_start_line = 1
        current_section_type = None
        current_section_name = None

        for idx, line in enumerate(lines, start=1):
            # Detect class or function definitions
            class_match = re.match(r'^class\s+(\w+)', line)
            func_match = re.match(r'^def\s+(\w+)', line)

            if class_match or func_match:
                # Save previous chunk if it exists
                if current_chunk_lines:
                    chunks.append(CodeChunk(
                        content='\n'.join(current_chunk_lines),
                        start_line=current_start_line,
                        end_line=idx - 1,
                        language='python',
                        section_type=current_section_type,
                        section_name=current_section_name
                    ))

                # Start new chunk
                current_chunk_lines = [line]
                current_start_line = idx

                if class_match:
                    current_section_type = 'class'
                    current_section_name = class_match.group(1)
                else:
                    current_section_type = 'function'
                    current_section_name = func_match.group(1)
            else:
                current_chunk_lines.append(line)

            # Split if chunk exceeds max size
            if len(current_chunk_lines) >= max_lines:
                chunks.append(CodeChunk(
                    content='\n'.join(current_chunk_lines),
                    start_line=current_start_line,
                    end_line=idx,
                    language='python',
                    section_type=current_section_type,
                    section_name=current_section_name
                ))

                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk_lines) - overlap_lines)
                current_chunk_lines = current_chunk_lines[overlap_start:]
                current_start_line = idx - overlap_lines + 1

        # Add final chunk
        if current_chunk_lines:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk_lines),
                start_line=current_start_line,
                end_line=len(lines),
                language='python',
                section_type=current_section_type,
                section_name=current_section_name
            ))

        return chunks

    def _chunk_typescript(
        self,
        content: str,
        max_lines: int,
        overlap_lines: int
    ) -> List[CodeChunk]:
        """
        Chunk TypeScript/JavaScript by interface/class/function.
        """
        lines = content.split('\n')
        chunks = []
        current_chunk_lines = []
        current_start_line = 1
        current_section_type = None
        current_section_name = None

        for idx, line in enumerate(lines, start=1):
            # Detect TypeScript constructs
            interface_match = re.match(r'^\s*(?:export\s+)?interface\s+(\w+)', line)
            class_match = re.match(r'^\s*(?:export\s+)?class\s+(\w+)', line)
            func_match = re.match(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', line)
            arrow_func_match = re.match(r'^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(', line)

            if interface_match or class_match or func_match or arrow_func_match:
                # Save previous chunk
                if current_chunk_lines:
                    chunks.append(CodeChunk(
                        content='\n'.join(current_chunk_lines),
                        start_line=current_start_line,
                        end_line=idx - 1,
                        language='typescript',
                        section_type=current_section_type,
                        section_name=current_section_name
                    ))

                # Start new chunk
                current_chunk_lines = [line]
                current_start_line = idx

                if interface_match:
                    current_section_type = 'interface'
                    current_section_name = interface_match.group(1)
                elif class_match:
                    current_section_type = 'class'
                    current_section_name = class_match.group(1)
                elif func_match:
                    current_section_type = 'function'
                    current_section_name = func_match.group(1)
                elif arrow_func_match:
                    current_section_type = 'function'
                    current_section_name = arrow_func_match.group(1)
            else:
                current_chunk_lines.append(line)

            # Split if exceeds max size
            if len(current_chunk_lines) >= max_lines:
                chunks.append(CodeChunk(
                    content='\n'.join(current_chunk_lines),
                    start_line=current_start_line,
                    end_line=idx,
                    language='typescript',
                    section_type=current_section_type,
                    section_name=current_section_name
                ))

                overlap_start = max(0, len(current_chunk_lines) - overlap_lines)
                current_chunk_lines = current_chunk_lines[overlap_start:]
                current_start_line = idx - overlap_lines + 1

        # Add final chunk
        if current_chunk_lines:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk_lines),
                start_line=current_start_line,
                end_line=len(lines),
                language='typescript',
                section_type=current_section_type,
                section_name=current_section_name
            ))

        return chunks

    def _chunk_markdown(
        self,
        content: str,
        max_lines: int
    ) -> List[CodeChunk]:
        """
        Chunk Markdown by headers.
        """
        lines = content.split('\n')
        chunks = []
        current_chunk_lines = []
        current_start_line = 1
        current_section_name = None

        for idx, line in enumerate(lines, start=1):
            # Detect headers (# Header)
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                # Save previous section
                if current_chunk_lines:
                    chunks.append(CodeChunk(
                        content='\n'.join(current_chunk_lines),
                        start_line=current_start_line,
                        end_line=idx - 1,
                        language='markdown',
                        section_type='section',
                        section_name=current_section_name
                    ))

                # Start new section
                current_chunk_lines = [line]
                current_start_line = idx
                current_section_name = header_match.group(2)
            else:
                current_chunk_lines.append(line)

            # Split if exceeds max size (no overlap for markdown)
            if len(current_chunk_lines) >= max_lines:
                chunks.append(CodeChunk(
                    content='\n'.join(current_chunk_lines),
                    start_line=current_start_line,
                    end_line=idx,
                    language='markdown',
                    section_type='section',
                    section_name=current_section_name
                ))
                current_chunk_lines = []
                current_start_line = idx + 1

        # Add final chunk
        if current_chunk_lines:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk_lines),
                start_line=current_start_line,
                end_line=len(lines),
                language='markdown',
                section_type='section',
                section_name=current_section_name
            ))

        return chunks

    def _chunk_generic(
        self,
        content: str,
        max_lines: int,
        overlap_lines: int
    ) -> List[CodeChunk]:
        """
        Generic chunking by line count with overlap.
        """
        lines = content.split('\n')
        chunks = []

        idx = 0
        while idx < len(lines):
            chunk_lines = lines[idx:idx + max_lines]

            chunks.append(CodeChunk(
                content='\n'.join(chunk_lines),
                start_line=idx + 1,
                end_line=min(idx + len(chunk_lines), len(lines)),
                language='generic'
            ))

            # Move forward with overlap
            idx += max_lines - overlap_lines

        return chunks


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to file

    Returns:
        Language name (python, typescript, markdown, etc.)
    """
    extension_map = {
        '.py': 'python',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.md': 'markdown',
        '.mdx': 'markdown',
        '.rs': 'rust',
        '.go': 'go',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
    }

    for ext, lang in extension_map.items():
        if file_path.endswith(ext):
            return lang

    return 'generic'
