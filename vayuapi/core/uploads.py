"""
File upload utilities for VayuAPI

Supports uploading ANY file type:
- Images: jpg, png, gif, bmp, svg, webp, ico, etc.
- Documents: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, csv, etc.
- Videos: mp4, avi, mov, wmv, flv, mkv, webm, etc.
- Audio: mp3, wav, ogg, flac, aac, m4a, etc.
- Archives: zip, rar, tar, gz, 7z, etc.
- Code: py, js, ts, java, cpp, html, css, json, xml, etc.
- And any other file type!
"""

from typing import Optional, BinaryIO
import tempfile
import shutil
import inspect
import os
import mimetypes


class UploadFile:
    """
    Uploaded file object compatible with Starlette UploadFile.

    Supports ALL file types - no restrictions!

    Example:
        ```python
        from vayuapi import File, UploadFile

        # Upload ANY file type
        @app.post("/upload/")
        async def upload_file(file: UploadFile = File(...)):
            contents = await file.read()

            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "extension": file.extension,
                "size": len(contents),
                "is_image": file.is_image(),
                "is_video": file.is_video(),
                "is_document": file.is_document(),
            }

        # Upload images
        @app.post("/upload-image/")
        async def upload_image(file: UploadFile = File(...)):
            if not file.is_image():
                raise HTTPException(400, "Only images allowed")
            await file.save(f"./uploads/{file.filename}")
            return {"message": "Image uploaded"}

        # Upload any file with validation
        @app.post("/upload-any/")
        async def upload_any(file: UploadFile = File(...)):
            # No validation needed - accepts everything!
            return {
                "filename": file.filename,
                "type": file.content_type,
                "category": file.get_category()
            }
        ```
    """

    def __init__(
            self,
            file: any = None,
            *,
            filename: Optional[str] = None,
            content_type: Optional[str] = None,
            size: Optional[int] = None,
            headers: Optional[dict] = None,
    ):
        # Handle Starlette UploadFile
        if hasattr(file, 'file'):
            self.file = file.file
            self.filename = filename or getattr(file, 'filename', None)
            self.content_type = content_type or getattr(file, 'content_type', None)
            self.size = size or getattr(file, 'size', None)
            self.headers = headers or getattr(file, 'headers', {})
        else:
            self.file = file
            self.filename = filename
            self.content_type = content_type
            self.size = size
            self.headers = headers or {}

    @property
    def extension(self) -> Optional[str]:
        """
        Get file extension (without dot).

        Returns:
            File extension like 'pdf', 'jpg', 'zip', etc.
        """
        if self.filename:
            _, ext = os.path.splitext(self.filename)
            return ext.lstrip('.').lower() if ext else None
        return None

    def guess_content_type(self) -> Optional[str]:
        """
        Guess content type from filename.

        Returns:
            MIME type string
        """
        if self.filename:
            guessed, _ = mimetypes.guess_type(self.filename)
            return guessed or self.content_type
        return self.content_type

    def is_image(self) -> bool:
        """
        Check if file is an image.

        Supports: jpg, jpeg, png, gif, bmp, svg, webp, ico, tiff, and more.
        """
        content_type = self.content_type or self.guess_content_type() or ""
        if content_type.startswith('image/'):
            return True

        if self.extension:
            image_exts = {
                'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
                'ico', 'tiff', 'tif', 'heic', 'heif', 'raw'
            }
            return self.extension in image_exts
        return False

    def is_video(self) -> bool:
        """
        Check if file is a video.

        Supports: mp4, avi, mov, wmv, flv, mkv, webm, and more.
        """
        content_type = self.content_type or self.guess_content_type() or ""
        if content_type.startswith('video/'):
            return True

        if self.extension:
            video_exts = {
                'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm',
                'm4v', '3gp', 'mpeg', 'mpg', 'ogv'
            }
            return self.extension in video_exts
        return False

    def is_audio(self) -> bool:
        """
        Check if file is audio.

        Supports: mp3, wav, ogg, flac, aac, m4a, and more.
        """
        content_type = self.content_type or self.guess_content_type() or ""
        if content_type.startswith('audio/'):
            return True

        if self.extension:
            audio_exts = {
                'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma',
                'opus', 'oga', 'mid', 'midi'
            }
            return self.extension in audio_exts
        return False

    def is_document(self) -> bool:
        """
        Check if file is a document.

        Supports: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, csv, and more.
        """
        content_type = self.content_type or self.guess_content_type() or ""
        doc_types = {
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument',
            'text/plain', 'text/csv', 'application/rtf'
        }
        if any(doc_type in content_type for doc_type in doc_types):
            return True

        if self.extension:
            doc_exts = {
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                'txt', 'csv', 'rtf', 'odt', 'ods', 'odp'
            }
            return self.extension in doc_exts
        return False

    def is_archive(self) -> bool:
        """
        Check if file is an archive.

        Supports: zip, rar, tar, gz, 7z, and more.
        """
        if self.extension:
            archive_exts = {
                'zip', 'rar', 'tar', 'gz', 'bz2', '7z', 'xz',
                'tgz', 'tbz2', 'tar.gz', 'tar.bz2'
            }
            return self.extension in archive_exts
        return False

    def is_code(self) -> bool:
        """
        Check if file is source code.

        Supports: py, js, ts, java, cpp, html, css, json, xml, and more.
        """
        content_type = self.content_type or self.guess_content_type() or ""
        if 'text/' in content_type or 'application/json' in content_type or 'application/xml' in content_type:
            if self.extension:
                code_exts = {
                    'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h',
                    'cs', 'rb', 'go', 'rs', 'php', 'html', 'css', 'scss',
                    'json', 'xml', 'yaml', 'yml', 'md', 'sh', 'bash', 'sql'
                }
                return self.extension in code_exts
        return False

    def get_category(self) -> str:
        """
        Get file category.

        Returns:
            'image', 'video', 'audio', 'document', 'archive', 'code', or 'other'
        """
        if self.is_image():
            return 'image'
        elif self.is_video():
            return 'video'
        elif self.is_audio():
            return 'audio'
        elif self.is_document():
            return 'document'
        elif self.is_archive():
            return 'archive'
        elif self.is_code():
            return 'code'
        else:
            return 'other'

    async def read(self, size: int = -1) -> bytes:
        """Read file contents."""
        if self.file is None:
            return b""

        # Handle async file
        if inspect.iscoroutinefunction(getattr(self.file, 'read', None)):
            if size == -1:
                return await self.file.read()
            return await self.file.read(size)

        # Handle sync file
        if hasattr(self.file, 'read'):
            if size == -1:
                return self.file.read()
            return self.file.read(size)

        # If file is already bytes
        if isinstance(self.file, bytes):
            return self.file

        return b""

    async def write(self, data: bytes) -> int:
        """Write data to file."""
        if self.file is None:
            return 0

        # Handle async file
        if inspect.iscoroutinefunction(getattr(self.file, 'write', None)):
            return await self.file.write(data)

        # Handle sync file
        if hasattr(self.file, 'write'):
            return self.file.write(data)

        return 0

    async def seek(self, offset: int) -> int:
        """Seek to position in file."""
        if self.file is None:
            return 0

        # Handle async file
        if inspect.iscoroutinefunction(getattr(self.file, 'seek', None)):
            return await self.file.seek(offset)

        # Handle sync file
        if hasattr(self.file, 'seek'):
            return self.file.seek(offset)

        return 0

    async def close(self):
        """Close the file."""
        if self.file is None:
            return

        # Handle async file
        if inspect.iscoroutinefunction(getattr(self.file, 'close', None)):
            await self.file.close()
        # Handle sync file
        elif hasattr(self.file, 'close'):
            self.file.close()

    async def save(self, destination: str):
        """
        Save uploaded file to destination.

        Args:
            destination: Path to save the file
        """
        # Read content
        await self.seek(0)  # Ensure we're at the beginning
        content = await self.read()

        # Write to destination
        with open(destination, 'wb') as f:
            f.write(content)

        # Reset file position
        await self.seek(0)

    def __repr__(self):
        return f"UploadFile(filename={self.filename}, content_type={self.content_type})"

    def __str__(self):
        return self.filename or "unnamed"


__all__ = ["UploadFile"]
