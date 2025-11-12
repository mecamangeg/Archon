# File: python/src/server/services/sync/hash_utils.py

import hashlib
from typing import BinaryIO


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA-256 hash
    """
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest()


def compute_content_hash(content: str) -> str:
    """
    Compute SHA-256 hash of string content.

    Args:
        content: String content

    Returns:
        Hex string of SHA-256 hash
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def compute_chunk_hash(chunk_content: str) -> str:
    """
    Compute hash for a code chunk.

    This is the same as compute_content_hash but semantically distinct.

    Args:
        chunk_content: Content of the chunk

    Returns:
        Hex string of SHA-256 hash
    """
    return compute_content_hash(chunk_content)


def hash_file_stream(file_obj: BinaryIO) -> str:
    """
    Compute hash from file object without loading entire file into memory.

    Args:
        file_obj: File object opened in binary mode

    Returns:
        Hex string of SHA-256 hash
    """
    hasher = hashlib.sha256()

    for chunk in iter(lambda: file_obj.read(8192), b''):
        hasher.update(chunk)

    return hasher.hexdigest()
