"""Small cross-pipeline helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def slug(s: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s[:max_len] or "untitled"


def run_id(prefix: str = "run") -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}"


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return p


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def file_to_data_url(path: str | Path) -> str:
    p = Path(path)
    mime, _ = mimetypes.guess_type(p.name)
    if not mime:
        mime = "application/octet-stream"
    b = p.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(b).decode('ascii')}"


def file_size_mb(path: str | Path) -> float:
    return Path(path).stat().st_size / 1_000_000


def assert_under_size(path: str | Path, max_mb: float = 5.0) -> None:
    size = file_size_mb(path)
    if size > max_mb:
        raise RuntimeError(f"{path} is {size:.2f} MB — over the {max_mb} MB ad-network limit.")


def strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip("` \n")
    return raw


def extract_docx_text(path: str | Path, max_chars: int = 30_000) -> str:
    """Extract plain text from a .docx file by parsing word/document.xml.

    No external deps — .docx is just a zip with XML. We pull the text content
    out of <w:t> elements concatenated with paragraph breaks. Capped at
    `max_chars` to keep prompts bounded.
    """
    import re as _re
    import zipfile as _zip

    p = Path(path)
    if not p.is_file() or p.suffix.lower() != ".docx":
        return ""
    try:
        with _zip.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return ""
    # Inject paragraph breaks at </w:p>, then strip all tags.
    xml = _re.sub(r"</w:p>", "\n", xml)
    text = _re.sub(r"<[^>]+>", " ", xml)
    text = _re.sub(r"\s+", " ", text)
    text = _re.sub(r" *\n *", "\n", text).strip()
    return text[:max_chars]


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Streaming SHA-256 of a file's content. Used as a cache key."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_first_frame(
    src: str | Path,
    out_path: str | Path,
    *,
    at_seconds: float = 3.0,
    width: int = 480,        # 720p in → 480p seed; ~50KB JPEG, well under any
                             # payload-size threshold the i2v endpoint may have
) -> Path:
    """Pull a representative frame from a video as a JPEG seed image.

    Used by creative_forge's grounded-i2v config: the chosen frame becomes
    the seed image for Scenario Seedance image-to-video, so the rendered ad
    starts from the actual game's pixels (not a hallucinated interpretation
    of a text prompt).

    Strategy: probe at 4 candidate offsets (`at_seconds`, ×2, ×4, ×6) and
    keep the largest JPEG. Larger == more entropy == past the loading /
    title-card frames the capture starts on. We saw mini_slayer's 0.5s
    frame was a near-blank 3KB while its 3s+ frames were 17KB of actual
    gameplay — picking by size gives us the gameplay frame for free.

    Falls back to a 1-byte stub if ffmpeg is missing (callers should treat
    that as "no seed image" and stay in text-only mode).
    """
    src_p, out_p = Path(src), Path(out_path)
    if not src_p.exists():
        raise FileNotFoundError(src_p)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        out_p.write_bytes(b"")
        return out_p

    candidates = [at_seconds, at_seconds * 2, at_seconds * 4, at_seconds * 6]
    best: tuple[int, Path] | None = None
    tmp_dir = out_p.parent
    for i, t in enumerate(candidates):
        tmp = tmp_dir / f".{out_p.stem}_cand{i}.jpg"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
            "-ss", str(t),
            "-i", str(src_p),
            "-frames:v", "1",
            "-vf", f"scale={width}:-2",
            "-q:v", "2",
            str(tmp),
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            continue
        if tmp.is_file():
            sz = tmp.stat().st_size
            if best is None or sz > best[0]:
                best = (sz, tmp)
    if best is None:
        out_p.write_bytes(b"")
        return out_p

    # Move winner to the requested out_path, clean up the others.
    best[1].replace(out_p)
    for i in range(len(candidates)):
        leftover = tmp_dir / f".{out_p.stem}_cand{i}.jpg"
        if leftover.exists():
            leftover.unlink(missing_ok=True)
    return out_p


def compress_video_for_analysis(
    src: str | Path,
    *,
    cache_dir: Path,
    max_height: int = 480,
    crf: int = 30,
    audio_bitrate: str = "64k",
) -> Path:
    """Downsample a video to a Gemini-friendly size.

    Default: scale to max 480p height, h264 CRF 30, mono 64kbps audio. A
    typical 100MB gameplay capture compresses to 5-10MB, which is the
    difference between "Gemini upload succeeds in 8s" and "upload retries
    three times and the workflow task exceeds 10 seconds".

    Cached by content hash → repeat calls with the same src are free. Output
    lives at `<cache_dir>/<sha256[:16]>.mp4`.

    Falls back to returning the original path if ffmpeg is missing.
    """
    src_p = Path(src)
    if not src_p.exists():
        raise FileNotFoundError(src_p)

    if shutil.which("ffmpeg") is None:
        return src_p

    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = file_sha256(src_p)[:16]
    out = cache_dir / f"{digest}.mp4"
    if out.exists() and out.stat().st_size > 0:
        return out

    # `-movflags +faststart` keeps the moov atom near the front so streaming
    # uploads (Gemini, Scenario) don't have to wait for the full file.
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
        "-i", str(src_p),
        "-vf", f"scale=-2:'min({max_height},ih)'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "aac", "-ac", "1", "-b:a", audio_bitrate,
        "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out
