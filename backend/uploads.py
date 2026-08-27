"""
uploads.py

Shared file-upload helper for the gallery (images) and notice board
(PDF attachments). Standalone — no chatbot dependency.

Files are saved with a random prefix to avoid collisions/overwrites,
using werkzeug's secure_filename to strip anything path-traversal-ish.
"""

import os
import uuid
from werkzeug.utils import secure_filename

STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
UPLOAD_ROOT = os.path.join(STATIC_ROOT, "uploads")

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
ALLOWED_DOC_EXT = {"pdf"}

MAX_IMAGE_DIMENSION = 1600  # px, longest side
JPEG_QUALITY = 82


def _extension(filename):
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _optimize_image(path):
    """
    Resizes down (never up) to a max dimension and re-compresses, so a
    12MB phone photo doesn't sit on disk/bandwidth at full resolution
    for what's shown as a ~300px gallery thumbnail. Animated GIFs are
    left untouched (resizing would break the animation). Any failure
    here just leaves the original upload as-is rather than breaking
    the upload — this is a nice-to-have, not something that should be
    able to fail the request.
    """

    try:
        from PIL import Image
    except ImportError:
        return  # Pillow not installed — skip optimization, keep original

    try:
        with Image.open(path) as img:
            fmt = img.format

            if fmt == "GIF":
                return

            width, height = img.size
            longest = max(width, height)

            if longest > MAX_IMAGE_DIMENSION:
                ratio = MAX_IMAGE_DIMENSION / float(longest)
                new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
                img = img.resize(new_size, Image.LANCZOS)

            if fmt == "JPEG":
                img.convert("RGB").save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            elif fmt == "PNG":
                img.save(path, format="PNG", optimize=True)
            elif fmt == "WEBP":
                img.save(path, format="WEBP", quality=JPEG_QUALITY)
            else:
                img.save(path)

    except Exception:
        pass


def save_upload(file_storage, subfolder, allowed_ext, optimize=False):
    """
    Saves an uploaded file into static/uploads/<subfolder>/.
    Returns the saved filename (not full path) on success, or None if
    there was no file or the extension isn't allowed.

    optimize=True additionally resizes/compresses image uploads (used
    for the gallery — not for PDF notice attachments).
    """

    if not file_storage or not file_storage.filename:
        return None

    ext = _extension(file_storage.filename)

    if ext not in allowed_ext:
        return None

    safe_name = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"

    folder = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(folder, exist_ok=True)

    full_path = os.path.join(folder, unique_name)
    file_storage.save(full_path)

    if optimize:
        _optimize_image(full_path)

    return unique_name


def delete_upload(filename, subfolder):
    if not filename:
        return
    path = os.path.join(UPLOAD_ROOT, subfolder, filename)
    if os.path.exists(path):
        os.remove(path)


def upload_url(filename, subfolder):
    if not filename:
        return None
    return f"/static/uploads/{subfolder}/{filename}"
