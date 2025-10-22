from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Set, DefaultDict
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import base64
import hashlib
import io
import tarfile
import time
import random
import sys
import os
import fnmatch
import re
from collections import defaultdict, deque


DEFAULT_API_BASE = "https://api.github.com"


def _slug_path(slug: str) -> str:
    return quote(slug, safe="/")


def _http_get(url: str, token: Optional[str], accept: str = "application/vnd.github+json") -> Dict:
    headers = {
        "Accept": accept,
        "User-Agent": "oqoqo-hot-path-pipeline",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            text = data.decode(charset, errors="replace")
            return json.loads(text)
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "<no-body>"
        raise RuntimeError(f"HTTP {e.code} for {url}: {err_body}") from e
    except URLError as e:
        raise RuntimeError(f"Network error for {url}: {e}") from e


def _get_default_branch(api_base: str, token: Optional[str], slug: str) -> str:
    url = f"{api_base}/repos/{_slug_path(slug)}"
    data = _http_get(url, token)
    branch = data.get("default_branch")
    if not branch:
        raise RuntimeError(f"Could not determine default branch for {slug}")
    return branch


def _resolve_branch_with_fallback(api_base: str, token: Optional[str], slug: str, branch: Optional[str]) -> str:
    """Resolve branch, falling back to default branch if specified branch doesn't exist."""
    if branch:
        try:
            # Try to get commit SHA to verify branch exists
            _get_commit_sha(api_base, token, slug, branch)
            return branch
        except RuntimeError as e:
            # If specified branch doesn't exist (HTTP 404 or "Could not resolve"), try default branch
            error_msg = str(e)
            if "HTTP 404" in error_msg or "Could not resolve branch" in error_msg:
                print(f"Warning: Branch '{branch}' not found for {slug}, using default branch", file=sys.stderr)
                return _get_default_branch(api_base, token, slug)
            else:
                raise
    else:
        return _get_default_branch(api_base, token, slug)


def _get_commit_sha(api_base: str, token: Optional[str], slug: str, branch: str) -> str:
    url = f"{api_base}/repos/{_slug_path(slug)}/git/ref/heads/{quote(branch, safe='')}"
    data = _http_get(url, token)
    obj = data.get("object") or {}
    sha = obj.get("sha")
    if not sha:
        raise RuntimeError(f"Could not resolve branch '{branch}' for {slug}")
    return sha


def list_repo_tree(api_base: str, token: Optional[str], slug: str, branch: Optional[str]) -> List[Dict]:
    # Try specified branch first, fall back to default branch if it doesn't exist
    ref = branch
    if ref:
        try:
            sha = _get_commit_sha(api_base, token, slug, ref)
        except RuntimeError as e:
            # If specified branch doesn't exist (HTTP 404 or "Could not resolve"), try default branch
            error_msg = str(e)
            if "HTTP 404" in error_msg or "Could not resolve branch" in error_msg:
                print(f"Warning: Branch '{ref}' not found for {slug}, using default branch", file=sys.stderr)
                ref = _get_default_branch(api_base, token, slug)
                sha = _get_commit_sha(api_base, token, slug, ref)
            else:
                raise
    else:
        ref = _get_default_branch(api_base, token, slug)
        sha = _get_commit_sha(api_base, token, slug, ref)
    url = f"{api_base}/repos/{_slug_path(slug)}/git/trees/{quote(sha, safe='')}?recursive=1"
    data = _http_get(url, token)
    tree = data.get("tree") or []
    truncated = data.get("truncated", False)
    if truncated:
        raise RuntimeError(
            f"Tree listing truncated for {slug}; repository may exceed GitHub API tree limit."
        )
    return tree


@dataclass
class PipelineSettings:
    merkle_tree_chunk_size: int = 1024
    rolling_hash_window_size: int = 32
    tree_edit_distance_threshold: float = 0.3
    louvain_resolution: float = 1.0
    min_community_size: int = 3
    minhash_num_perm: int = 128
    lsh_num_bands: int = 16
    lsh_rows_per_band: int = 8
    similarity_threshold: float = 0.7
    max_file_size_mb: int = 10
    max_analysis_time_seconds: int = 300
    enable_parallel_processing: bool = True
    max_workers: int = 4
    output_format: str = "json"
    verbose: bool = False
    debug: bool = False
    # Similarity analysis controls
    similarity_max_files: int = 2000
    similarity_max_tokens_per_file: int = 4000
    similarity_progress_every: int = 200
    similarity_max_pairs: int = 50000
    similarity_cross_only: bool = True
    similarity_exclude_binary: bool = True
    similarity_include_globs: List[str] = field(default_factory=lambda: ["*"])
    similarity_exclude_globs: List[str] = field(
        default_factory=lambda: [
            "*/node_modules/*",
            "*/dist/*",
            "*/build/*",
            "*/.git/*",
            "*/.next/*",
            "*/.cache/*",
            "*/coverage/*",
            "*/vendor/*",
            "*/target/*",
            "*/.venv/*",
            "*/__pycache__/*",
            "*.lock",
        ]
    )
    similarity_text_normalize: bool = True
    similarity_text_extensions: List[str] = field(
        default_factory=lambda: [
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".json",
            ".md",
            ".py",
            ".java",
            ".go",
            ".rb",
            ".php",
            ".css",
            ".scss",
            ".html",
            ".xml",
            ".yml",
            ".yaml",
            ".sh",
            ".c",
            ".h",
            ".cpp",
            ".hpp",
        ]
    )
    similarity_binary_extensions: List[str] = field(
        default_factory=lambda: [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".avif",
            ".mp3",
            ".mp4",
            ".mov",
            ".wav",
            ".pdf",
            ".zip",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".tar",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".otf",
            ".bin",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".wasm",
        ]
    )


def load_settings(cfg: Dict) -> PipelineSettings:
    return PipelineSettings(
        merkle_tree_chunk_size=int(cfg.get("merkle_tree_chunk_size", 1024)),
        rolling_hash_window_size=int(cfg.get("rolling_hash_window_size", 32)),
        tree_edit_distance_threshold=float(cfg.get("tree_edit_distance_threshold", 0.3)),
        louvain_resolution=float(cfg.get("louvain_resolution", 1.0)),
        min_community_size=int(cfg.get("min_community_size", 3)),
        minhash_num_perm=int(cfg.get("minhash_num_perm", 128)),
        lsh_num_bands=int(cfg.get("lsh_num_bands", 16)),
        lsh_rows_per_band=int(cfg.get("lsh_rows_per_band", 8)),
        similarity_threshold=float(cfg.get("similarity_threshold", 0.7)),
        max_file_size_mb=int(cfg.get("max_file_size_mb", 10)),
        max_analysis_time_seconds=int(cfg.get("max_analysis_time_seconds", 300)),
        enable_parallel_processing=bool(cfg.get("enable_parallel_processing", True)),
        max_workers=int(cfg.get("max_workers", 4)),
        output_format=str(cfg.get("output_format", "json")),
        verbose=bool(cfg.get("verbose", False)),
        debug=bool(cfg.get("debug", False)),
        similarity_max_files=int(cfg.get("similarity_max_files", 2000)),
        similarity_max_tokens_per_file=int(cfg.get("similarity_max_tokens_per_file", 4000)),
        similarity_progress_every=int(cfg.get("similarity_progress_every", 200)),
        similarity_max_pairs=int(cfg.get("similarity_max_pairs", 50000)),
        similarity_cross_only=bool(cfg.get("similarity_cross_only", True)),
        similarity_exclude_binary=bool(cfg.get("similarity_exclude_binary", True)),
        similarity_include_globs=list(cfg.get("similarity_include_globs", ["*"])),
        similarity_exclude_globs=list(
            cfg.get(
                "similarity_exclude_globs",
                [
                    "*/node_modules/*",
                    "*/dist/*",
                    "*/build/*",
                    "*/.git/*",
                    "*/.next/*",
                    "*/.cache/*",
                    "*/coverage/*",
                    "*/vendor/*",
                    "*/target/*",
                    "*/.venv/*",
                    "*/__pycache__/*",
                    "*.lock",
                ],
            )
        ),
        similarity_text_normalize=bool(cfg.get("similarity_text_normalize", True)),
        similarity_text_extensions=list(
            cfg.get(
                "similarity_text_extensions",
                [
                    ".js",
                    ".ts",
                    ".tsx",
                    ".jsx",
                    ".json",
                    ".md",
                    ".py",
                    ".java",
                    ".go",
                    ".rb",
                    ".php",
                    ".css",
                    ".scss",
                    ".html",
                    ".xml",
                    ".yml",
                    ".yaml",
                    ".sh",
                    ".c",
                    ".h",
                    ".cpp",
                    ".hpp",
                ],
            )
        ),
        similarity_binary_extensions=list(
            cfg.get(
                "similarity_binary_extensions",
                [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".svg",
                    ".ico",
                    ".webp",
                    ".avif",
                    ".mp3",
                    ".mp4",
                    ".mov",
                    ".wav",
                    ".pdf",
                    ".zip",
                    ".gz",
                    ".bz2",
                    ".7z",
                    ".rar",
                    ".tar",
                    ".woff",
                    ".woff2",
                    ".ttf",
                    ".eot",
                    ".otf",
                    ".bin",
                    ".exe",
                    ".dll",
                    ".so",
                    ".dylib",
                    ".wasm",
                ],
            )
        ),
    )


def summarize_repo(api_base: str, token: Optional[str], slug: str, branch: Optional[str], settings: PipelineSettings) -> Dict:
    tree = list_repo_tree(api_base, token, slug, branch)
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    total_files = 0
    total_bytes = 0
    skipped_large = 0
    for node in tree:
        if node.get("type") != "blob":
            continue
        total_files += 1
        size = int(node.get("size") or 0)
        if size > max_bytes:
            skipped_large += 1
            continue
        total_bytes += size
    return {
        "files": total_files,
        "bytes": total_bytes,
        "skipped_large": skipped_large,
    }


# --- Chunking and Merkle hashing ---

def _chunks(data: bytes, size: int) -> Iterable[bytes]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


def merkle_root_for_bytes(data: bytes, chunk_size: int) -> Tuple[str, int]:
    """Compute a simple binary Merkle root over fixed-size chunks.

    Returns (root_hex, num_chunks). If data is empty, returns sha256("") and 0.
    """
    if not data:
        return hashlib.sha256(b"").hexdigest(), 0
    leaves = [hashlib.sha256(c).digest() for c in _chunks(data, chunk_size)]
    n_chunks = len(leaves)
    if n_chunks == 1:
        return hashlib.sha256(leaves[0]).hexdigest(), n_chunks
    layer = leaves
    while len(layer) > 1:
        nxt: List[bytes] = []
        it = iter(layer)
        for a in it:
            try:
                b = next(it)
            except StopIteration:
                # Duplicate last node if odd fanout
                b = a
            nxt.append(hashlib.sha256(a + b).digest())
        layer = nxt
    return hashlib.sha256(layer[0]).hexdigest(), n_chunks


def _get_blob(api_base: str, token: Optional[str], slug: str, sha: str) -> Dict:
    url = f"{api_base}/repos/{_slug_path(slug)}/git/blobs/{quote(sha, safe='')}"
    return _http_get(url, token)


def analyze_repo_merkle(
    api_base: str,
    token: Optional[str],
    slug: str,
    branch: Optional[str],
    settings: PipelineSettings,
) -> Dict:
    """Compute Merkle stats by downloading a single repo tarball for the ref.

    This is much faster and avoids rate limits compared to per-blob fetches.
    """
    ref = _resolve_branch_with_fallback(api_base, token, slug, branch)
    tar_bytes = _get_repo_tarball(api_base, token, slug, ref)
    tf = tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz")
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    hashed_files = 0
    total_chunks = 0
    errors = 0
    skipped_large = 0
    start = time.monotonic()
    for m in tf.getmembers():
        if not m.isfile():
            continue
        if m.size > max_bytes:
            skipped_large += 1
            continue
        try:
            f = tf.extractfile(m)
            if not f:
                continue
            data = f.read()
            _, n_chunks = merkle_root_for_bytes(data, settings.merkle_tree_chunk_size)
            hashed_files += 1
            total_chunks += n_chunks
        except Exception:
            errors += 1
        # Respect time limit
        if settings.max_analysis_time_seconds and (
            time.monotonic() - start > settings.max_analysis_time_seconds
        ):
            break
    elapsed = time.monotonic() - start
    return {
        "hashed_files": hashed_files,
        "total_chunks": total_chunks,
        "errors": errors,
        "skipped_large": skipped_large,
        "elapsed_seconds": round(elapsed, 3),
        "ref": ref,
    }


def _http_get_bytes(url: str, token: Optional[str]) -> bytes:
    headers = {
        "User-Agent": "oqoqo-hot-path-pipeline",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.read()
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "<no-body>"
        raise RuntimeError(f"HTTP {e.code} for {url}: {err_body}") from e
    except URLError as e:
        raise RuntimeError(f"Network error for {url}: {e}") from e


def _get_repo_tarball(api_base: str, token: Optional[str], slug: str, ref: str) -> bytes:
    url = f"{api_base}/repos/{_slug_path(slug)}/tarball/{quote(ref, safe='')}"
    return _http_get_bytes(url, token)


# --- Similarity pipeline: MinHash + LSH ---

def _strip_tar_leading_dir(path: str) -> str:
    parts = path.split("/", 1)
    return parts[1] if len(parts) > 1 else path


def _file_tokens_from_bytes(data: bytes, window: int, max_tokens: int) -> Set[int]:
    if not data or window <= 0 or len(data) < window:
        return set()
    stride = max(1, window // 4)
    tokens: Set[int] = set()
    for i in range(0, len(data) - window + 1, stride):
        h = hashlib.blake2b(data[i : i + window], digest_size=8).digest()
        tokens.add(int.from_bytes(h, "big"))
        if len(tokens) >= max_tokens:
            break
    return tokens


def _should_consider_path(path: str, settings: PipelineSettings) -> bool:
    # Includes take precedence; if none match, skip
    if settings.similarity_include_globs:
        if not any(fnmatch.fnmatch(path, pat) for pat in settings.similarity_include_globs):
            return False
    # Excludes remove matches
    if any(fnmatch.fnmatch(path, pat) for pat in settings.similarity_exclude_globs):
        return False
    return True


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _is_binary_ext(path: str, settings: PipelineSettings) -> bool:
    ext = _ext(path)
    # Normalize configured extensions to lowercase with leading dot
    bin_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in settings.similarity_binary_extensions}
    return ext in bin_set


def _is_text_ext(path: str, settings: PipelineSettings) -> bool:
    ext = _ext(path)
    txt_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in settings.similarity_text_extensions}
    return ext in txt_set


def _normalize_text(data: bytes, ext: str) -> bytes:
    # Decode with fallback
    try:
        s = data.decode("utf-8")
    except UnicodeDecodeError:
        s = data.decode("latin-1", errors="ignore")
    s = s.replace("\r", "")
    # Extension-specific light normalization
    if ext in {".js", ".ts", ".tsx", ".jsx", ".css", ".scss", ".java", ".go", ".rb", ".php", ".c", ".h", ".cpp", ".hpp", ".sh"}:
        # Remove //... and /*...*/ comments
        import re

        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
        s = re.sub(r"//.*", " ", s)
    if ext in {".json"}:
        try:
            obj = json.loads(s)
            s = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        except Exception:
            pass
    if ext in {".md"}:
        import re

        # Strip code fences and links
        s = re.sub(r"```[\s\S]*?```", " ", s)
        s = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", s)
    # Collapse whitespace and lowercase
    s = " ".join(s.split()).lower()
    return s.encode("utf-8")


def _minhash_params(num_perm: int, seed: int = 42) -> Tuple[List[int], List[int], int]:
    rnd = random.Random(seed)
    P = 2305843009213693951  # 2^61-1
    a = [rnd.randrange(1, P - 1) for _ in range(num_perm)]
    b = [rnd.randrange(0, P - 1) for _ in range(num_perm)]
    return a, b, P


def _minhash_signature(tokens: Set[int], a: List[int], b: List[int], P: int) -> List[int]:
    if not tokens:
        return [P - 1 for _ in range(len(a))]
    sig = [P - 1] * len(a)
    for x in tokens:
        for i in range(len(a)):
            val = (a[i] * x + b[i]) % P
            if val < sig[i]:
                sig[i] = val
    return sig


def _lsh_candidates(signatures: Dict[str, List[int]], num_bands: int, rows_per_band: int) -> Set[Tuple[str, str]]:
    buckets: DefaultDict[Tuple[int, Tuple[int, ...]], List[str]] = defaultdict(list)
    if not signatures:
        return set()
    k = len(next(iter(signatures.values())))
    if k == 0:
        return set()
    # Ensure we don't slice beyond signature length
    if num_bands * rows_per_band > k:
        rows_per_band = max(1, k // max(1, num_bands))
    for fid, sig in signatures.items():
        for bidx in range(num_bands):
            start = bidx * rows_per_band
            end = min(start + rows_per_band, len(sig))
            if start >= end:
                break
            key = (bidx, tuple(sig[start:end]))
            buckets[key].append(fid)
    pairs: Set[Tuple[str, str]] = set()
    for ids in buckets.values():
        if len(ids) < 2:
            continue
        n = len(ids)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = ids[i], ids[j]
                if a > b:
                    a, b = b, a
                pairs.add((a, b))
    return pairs


def _sig_similarity(sig_a: List[int], sig_b: List[int]) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    eq = sum(1 for x, y in zip(sig_a, sig_b) if x == y)
    return eq / float(len(sig_a))


def analyze_similarity(
    api_base: str,
    token: Optional[str],
    code_slug: str,
    code_branch: Optional[str],
    docs_slug: str,
    docs_branch: Optional[str],
    settings: PipelineSettings,
) -> Dict:
    start = time.monotonic()
    code_ref = _resolve_branch_with_fallback(api_base, token, code_slug, code_branch)
    docs_ref = _resolve_branch_with_fallback(api_base, token, docs_slug, docs_branch)
    code_tar = _get_repo_tarball(api_base, token, code_slug, code_ref)
    docs_tar = _get_repo_tarball(api_base, token, docs_slug, docs_ref)

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    window = settings.rolling_hash_window_size

    code_tf = tarfile.open(fileobj=io.BytesIO(code_tar), mode="r:gz")
    docs_tf = tarfile.open(fileobj=io.BytesIO(docs_tar), mode="r:gz")

    meta_by_id: Dict[str, Dict] = {}
    signatures: Dict[str, List[int]] = {}
    num_perm = settings.minhash_num_perm
    a, b, P = _minhash_params(num_perm)

    def add_repo(tf: tarfile.TarFile, kind: str, limit: int) -> int:
        processed = 0
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size > max_bytes:
                continue
            path = _strip_tar_leading_dir(m.name)
            if not _should_consider_path(path, settings):
                continue
            if settings.similarity_exclude_binary and _is_binary_ext(path, settings):
                continue
            fid = f"{kind}:{path}"
            try:
                f = tf.extractfile(m)
                data = f.read() if f else b""
            except Exception:
                data = b""
            if settings.similarity_text_normalize and _is_text_ext(path, settings):
                data = _normalize_text(data, _ext(path))
            tokens = _file_tokens_from_bytes(data, window, settings.similarity_max_tokens_per_file)
            sig = _minhash_signature(tokens, a, b, P)
            meta_by_id[fid] = {"kind": kind, "path": path, "size": m.size}
            signatures[fid] = sig
            processed += 1
            if settings.verbose and processed % max(1, settings.similarity_progress_every) == 0:
                print(f"[{kind}] processed {processed} files...", file=sys.stderr)
            # Time budget
            if settings.max_analysis_time_seconds and (time.monotonic() - start > settings.max_analysis_time_seconds):
                break
            if processed >= limit:
                break
        return processed

    # Split max files budget roughly equally between repos
    per_repo_limit = max(1, settings.similarity_max_files // 2)
    count_code = add_repo(code_tf, "code", per_repo_limit)
    # Remaining budget for docs + ensure at least 1
    remaining = max(1, settings.similarity_max_files - count_code)
    add_repo(docs_tf, "docs", remaining)

    bands = settings.lsh_num_bands
    rows = settings.lsh_rows_per_band
    candidates = _lsh_candidates(signatures, bands, rows)
    # Truncate excessive candidate pairs
    truncated_pairs = False
    if len(candidates) > settings.similarity_max_pairs:
        candidates = set(list(candidates)[: settings.similarity_max_pairs])
        truncated_pairs = True

    threshold = settings.similarity_threshold
    edges: List[Tuple[str, str, float]] = []
    adj: DefaultDict[str, List[str]] = defaultdict(list)
    for a_id, b_id in candidates:
        if settings.similarity_cross_only:
            if meta_by_id.get(a_id, {}).get("kind") == meta_by_id.get(b_id, {}).get("kind"):
                continue
        s = _sig_similarity(signatures[a_id], signatures[b_id])
        if s >= threshold:
            edges.append((a_id, b_id, s))
            adj[a_id].append(b_id)
            adj[b_id].append(a_id)

    visited: Set[str] = set()
    communities: List[List[str]] = []
    for node in meta_by_id.keys():
        if node in visited:
            continue
        comp: List[str] = []
        dq = deque([node])
        visited.add(node)
        while dq:
            cur = dq.popleft()
            comp.append(cur)
            for nb in adj.get(cur, []):
                if nb not in visited:
                    visited.add(nb)
                    dq.append(nb)
        if len(comp) >= max(1, settings.min_community_size):
            communities.append(comp)

    elapsed = time.monotonic() - start
    return {
        "files": len(meta_by_id),
        "candidates": len(candidates),
        "edges": len(edges),
        "communities": communities,
        "top_pairs": sorted(edges, key=lambda e: e[2], reverse=True)[:20],
        "code_ref": code_ref,
        "docs_ref": docs_ref,
        "num_perm": num_perm,
        "bands": bands,
        "rows": rows,
        "window": window,
        "threshold": threshold,
        "elapsed_seconds": round(elapsed, 3),
        "truncated_pairs": truncated_pairs,
    }


# --- Layer 3: Community discovery on a pragmatic call graph ---

def _iter_code_files_from_tar(tar_bytes: bytes, settings: PipelineSettings) -> Iterable[Tuple[str, bytes]]:
    tf = tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz")
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    for m in tf.getmembers():
        if not m.isfile():
            continue
        path = _strip_tar_leading_dir(m.name)
        if m.size > max_bytes:
            continue
        if not _should_consider_path(path, settings):
            continue
        if settings.similarity_exclude_binary and _is_binary_ext(path, settings):
            continue
        try:
            f = tf.extractfile(m)
            data = f.read() if f else b""
        except Exception:
            data = b""
        yield path, data


_RE_FUNC_JS = re.compile(r"(?:export\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_RE_FUNC_VAR_JS = re.compile(r"(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:function\s*\(|\([\s\S]*?\)\s*=>)")
_RE_CALL_JS = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _extract_functions_and_calls_js(path: str, data: bytes) -> Tuple[Set[str], Dict[str, Set[str]]]:
    try:
        s = data.decode("utf-8")
    except UnicodeDecodeError:
        s = data.decode("latin-1", errors="ignore")
    # Strip comments quickly to reduce noise
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"//.*", " ", s)
    funcs = set(_RE_FUNC_JS.findall(s)) | set(_RE_FUNC_VAR_JS.findall(s))
    calls_by_func: Dict[str, Set[str]] = {}
    # Very naive scoping: attribute calls "obj.fn(" will capture fn; ignore very common words
    stop = {"if", "for", "while", "switch", "return", "function", "console", "new", "catch", "typeof", "await"}
    # Attribute-based match: a.b() yields b; we accept that risk
    # Split by function bodies approximately to associate calls with definiers
    for name in funcs:
        calls_by_func[name] = set()
    # Global file scope node to catch unscoped calls
    file_scope = "__file__"
    calls_by_func[file_scope] = set()
    for m in _RE_CALL_JS.finditer(s):
        callee = m.group(1)
        if callee in stop:
            continue
        # Assign to file scope; mapping to specific function body is complex without a parser
        calls_by_func[file_scope].add(callee)
    return funcs, calls_by_func


def _louvain_community_detection(adj: Dict[str, Set[str]], resolution: float = 1.0) -> Dict[str, str]:
    """
    Use Louvain algorithm for community detection.
    Falls back to label propagation if Louvain not available.

    Args:
        adj: Adjacency list representation of graph
        resolution: Resolution parameter for Louvain (higher = smaller communities)

    Returns:
        Dict mapping node -> community label
    """
    try:
        import networkx as nx
        import community as community_louvain

        # Build NetworkX graph
        G = nx.Graph()
        for node, neighbors in adj.items():
            G.add_node(node)
            for neighbor in neighbors:
                G.add_edge(node, neighbor)

        # Run Louvain algorithm
        partition = community_louvain.best_partition(G, resolution=resolution)

        # Convert community IDs to string labels
        labels = {node: f"community_{comm_id}" for node, comm_id in partition.items()}
        return labels

    except ImportError:
        # Fallback to label propagation
        return _label_propagation_fallback(adj)


def _label_propagation_fallback(adj: Dict[str, Set[str]], max_iter: int = 10, seed: int = 42) -> Dict[str, str]:
    """Fallback community detection using label propagation"""
    rnd = random.Random(seed)
    labels: Dict[str, str] = {n: n for n in adj.keys()}
    nodes = list(adj.keys())
    for _ in range(max_iter):
        rnd.shuffle(nodes)
        changes = 0
        for n in nodes:
            counts: DefaultDict[str, int] = defaultdict(int)
            for nb in adj.get(n, []):
                counts[labels[nb]] += 1
            if not counts:
                continue
            # pick the label with max frequency; deterministic tie-breaker
            best_label = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
            if labels[n] != best_label:
                labels[n] = best_label
                changes += 1
        if changes == 0:
            break
    return labels


def analyze_communities(
    api_base: str,
    token: Optional[str],
    code_slug: str,
    code_branch: Optional[str],
    settings: PipelineSettings,
) -> Dict:
    start = time.monotonic()
    ref = _resolve_branch_with_fallback(api_base, token, code_slug, code_branch)
    tar = _get_repo_tarball(api_base, token, code_slug, ref)

    # Build a pragmatic call graph over JS/TS files (fallback if other langs)
    defined_funcs: Dict[str, str] = {}  # func name -> node id
    adj: DefaultDict[str, Set[str]] = defaultdict(set)
    nodes_meta: Dict[str, Dict] = {}

    for path, data in _iter_code_files_from_tar(tar, settings):
        ext = _ext(path)
        if ext not in {".js", ".ts", ".tsx", ".jsx"}:  # simple focus
            continue
        funcs, calls = _extract_functions_and_calls_js(path, data)
        for fn in funcs:
            node_id = f"{path}::${fn}"
            defined_funcs[fn] = node_id if fn not in defined_funcs else defined_funcs[fn]
            adj.setdefault(node_id, set())
            nodes_meta[node_id] = {"path": path, "name": fn}
        # Ensure a file-scope node exists to attach calls when no function known
        file_node = f"{path}::$__file__"
        adj.setdefault(file_node, set())
        nodes_meta[file_node] = {"path": path, "name": "__file__"}
        for src_fn, callees in calls.items():
            src_node = f"{path}::${src_fn}" if src_fn != "__file__" else file_node
            adj.setdefault(src_node, set())
            for callee in callees:
                dst_node = defined_funcs.get(callee)
                if not dst_node:
                    continue
                adj[src_node].add(dst_node)

    # Symmetrize for community detection on undirected graph
    undirected: DefaultDict[str, Set[str]] = defaultdict(set)
    for a, nbrs in adj.items():
        for b in nbrs:
            undirected[a].add(b)
            undirected[b].add(a)

    # Run Louvain community detection (falls back to label propagation if unavailable)
    labels = _louvain_community_detection(undirected, resolution=settings.louvain_resolution)
    # Group by label
    comm_map: DefaultDict[str, List[str]] = defaultdict(list)
    for n, lab in labels.items():
        comm_map[lab].append(n)
    communities = [members for members in comm_map.values() if len(members) >= max(1, settings.min_community_size)]

    elapsed = time.monotonic() - start
    edges_count = sum(len(v) for v in undirected.values()) // 2
    return {
        "ref": ref,
        "nodes": len(undirected),
        "edges": edges_count,
        "communities": communities,
        "elapsed_seconds": round(elapsed, 3),
    }


# --- Layer 2: Semantic Understanding via Tree Edit Distance ---

def analyze_semantic_diff(
    api_base: str,
    token: Optional[str],
    code_slug: str,
    old_ref: str,  # Can be branch name or commit SHA
    new_ref: str,  # Can be branch name or commit SHA
    settings: PipelineSettings,
) -> Dict:
    """Analyze semantic changes between two versions of a repository.

    Uses Zhang-Shasha tree edit distance to classify changes as:
    - identical: No change
    - refactor: Structural change, same logic
    - minor: Small logic changes
    - major: Significant logic changes
    - rewrite: Complete rewrite

    Args:
        api_base: GitHub API base URL
        token: GitHub token
        code_slug: Repository slug (owner/name)
        old_ref: Old version (branch or SHA)
        new_ref: New version (branch or SHA)
        settings: Pipeline settings

    Returns:
        Dict containing:
        - files_analyzed: Number of files compared
        - changes: List of file changes with semantic classification
        - summary: Aggregate statistics
        - elapsed_seconds: Time taken
    """
    try:
        from . import semantic
    except Exception:
        import semantic

    start = time.monotonic()

    # Resolve refs if they're branch names, with fallback to default branch
    try:
        old_sha = _get_commit_sha(api_base, token, code_slug, old_ref)
    except RuntimeError as e:
        # If branch doesn't exist, try default branch
        error_msg = str(e)
        if "HTTP 404" in error_msg or "Could not resolve branch" in error_msg:
            print(f"Warning: Branch '{old_ref}' not found for {code_slug}, using default branch", file=sys.stderr)
            old_ref = _get_default_branch(api_base, token, code_slug)
            old_sha = _get_commit_sha(api_base, token, code_slug, old_ref)
        else:
            # Assume it's already a SHA
            old_sha = old_ref

    try:
        new_sha = _get_commit_sha(api_base, token, code_slug, new_ref)
    except RuntimeError as e:
        # If branch doesn't exist, try default branch
        error_msg = str(e)
        if "HTTP 404" in error_msg or "Could not resolve branch" in error_msg:
            print(f"Warning: Branch '{new_ref}' not found for {code_slug}, using default branch", file=sys.stderr)
            new_ref = _get_default_branch(api_base, token, code_slug)
            new_sha = _get_commit_sha(api_base, token, code_slug, new_ref)
        else:
            # Assume it's already a SHA
            new_sha = new_ref

    # Fetch tarballs for both versions
    old_tar = _get_repo_tarball(api_base, token, code_slug, old_sha)
    new_tar = _get_repo_tarball(api_base, token, code_slug, new_sha)

    old_tf = tarfile.open(fileobj=io.BytesIO(old_tar), mode="r:gz")
    new_tf = tarfile.open(fileobj=io.BytesIO(new_tar), mode="r:gz")

    max_bytes = settings.max_file_size_mb * 1024 * 1024

    # Extract files from both versions
    old_files: Dict[str, bytes] = {}
    new_files: Dict[str, bytes] = {}

    for m in old_tf.getmembers():
        if not m.isfile() or m.size > max_bytes:
            continue
        path = _strip_tar_leading_dir(m.name)
        if not _should_consider_path(path, settings):
            continue
        try:
            f = old_tf.extractfile(m)
            if f:
                old_files[path] = f.read()
        except Exception:
            pass

    for m in new_tf.getmembers():
        if not m.isfile() or m.size > max_bytes:
            continue
        path = _strip_tar_leading_dir(m.name)
        if not _should_consider_path(path, settings):
            continue
        try:
            f = new_tf.extractfile(m)
            if f:
                new_files[path] = f.read()
        except Exception:
            pass

    # Find common files and analyze semantic changes
    common_paths = set(old_files.keys()) & set(new_files.keys())

    differ = semantic.SemanticDiff()
    changes: List[Dict] = []

    # Track statistics
    stats = {
        "identical": 0,
        "refactor": 0,
        "minor": 0,
        "major": 0,
        "rewrite": 0,
    }

    files_analyzed = 0
    for path in sorted(common_paths):
        # Determine language from extension
        ext = _ext(path)
        language = None
        if ext in {".py"}:
            language = "python"
        elif ext in {".js", ".jsx"}:
            language = "javascript"
        elif ext in {".ts", ".tsx"}:
            language = "typescript"

        if not language:
            continue  # Skip unsupported languages

        # Decode files
        try:
            old_code = old_files[path].decode('utf-8')
            new_code = new_files[path].decode('utf-8')
        except UnicodeDecodeError:
            continue  # Skip binary or non-UTF8 files

        # Skip if identical
        if old_code == new_code:
            stats["identical"] += 1
            continue

        # Analyze semantic change
        result = differ.analyze_change(
            old_code,
            new_code,
            language,
            threshold_refactor=0.1,
            threshold_minor=settings.tree_edit_distance_threshold,
            threshold_major=0.6,
        )

        change_type = result["change_type"].value
        stats[change_type] = stats.get(change_type, 0) + 1

        changes.append({
            "path": path,
            "language": language,
            "change_type": change_type,
            "distance": result["distance"],
            "normalized_distance": result["normalized_distance"],
            "size_old": result["size1"],
            "size_new": result["size2"],
            "needs_doc_update": differ.should_update_documentation(result),
        })

        files_analyzed += 1

        # Time limit
        if settings.max_analysis_time_seconds and (time.monotonic() - start > settings.max_analysis_time_seconds):
            break

    elapsed = time.monotonic() - start

    # Summary
    needs_doc_update = [c for c in changes if c["needs_doc_update"]]

    return {
        "old_ref": old_ref,
        "new_ref": new_ref,
        "old_sha": old_sha,
        "new_sha": new_sha,
        "files_analyzed": files_analyzed,
        "files_added": len(set(new_files.keys()) - set(old_files.keys())),
        "files_deleted": len(set(old_files.keys()) - set(new_files.keys())),
        "changes": changes[:100],  # Limit to top 100
        "changes_total": len(changes),
        "summary": stats,
        "needs_doc_update_count": len(needs_doc_update),
        "needs_doc_update": [c["path"] for c in needs_doc_update[:20]],
        "elapsed_seconds": round(elapsed, 3),
    }


# --- Layer 4: Cross-Reference Analysis with Aho-Corasick ---

def analyze_cross_references(
    api_base: str,
    token: Optional[str],
    code_slug: str,
    code_branch: Optional[str],
    docs_slug: str,
    docs_branch: Optional[str],
    settings: PipelineSettings,
) -> Dict:
    """
    Analyze cross-references between code entities and documentation.

    Uses Aho-Corasick algorithm to find all mentions of code entities
    (functions, classes) in documentation in O(n + k + z) time.

    This answers the critical question: "Which docs mention this function?"

    Args:
        api_base: GitHub API base URL
        token: GitHub token
        code_slug: Code repository slug
        code_branch: Code branch
        docs_slug: Documentation repository slug
        docs_branch: Documentation branch
        settings: Pipeline settings

    Returns:
        Dict containing:
        - total_entities: Number of code entities found
        - total_docs: Number of documentation files
        - cross_references: Entity -> docs mapping
        - impacted_docs: Which docs mention which entities
        - elapsed_seconds: Time taken
    """
    try:
        from . import pattern_matching
    except Exception:
        import pattern_matching

    start = time.monotonic()

    # Fetch code and docs
    code_ref = _resolve_branch_with_fallback(api_base, token, code_slug, code_branch)
    docs_ref = _resolve_branch_with_fallback(api_base, token, docs_slug, docs_branch)

    code_tar = _get_repo_tarball(api_base, token, code_slug, code_ref)
    docs_tar = _get_repo_tarball(api_base, token, docs_slug, docs_ref)

    code_tf = tarfile.open(fileobj=io.BytesIO(code_tar), mode="r:gz")
    docs_tf = tarfile.open(fileobj=io.BytesIO(docs_tar), mode="r:gz")

    max_bytes = settings.max_file_size_mb * 1024 * 1024

    # Extract code files
    code_files: Dict[str, Tuple[str, str]] = {}  # {path: (code, language)}
    for m in code_tf.getmembers():
        if not m.isfile() or m.size > max_bytes:
            continue
        path = _strip_tar_leading_dir(m.name)
        if not _should_consider_path(path, settings):
            continue

        ext = _ext(path)
        language = None
        if ext == ".py":
            language = "python"
        elif ext in {".js", ".jsx"}:
            language = "javascript"
        elif ext in {".ts", ".tsx"}:
            language = "typescript"

        if language:
            try:
                f = code_tf.extractfile(m)
                if f:
                    code = f.read().decode('utf-8', errors='ignore')
                    code_files[path] = (code, language)
            except Exception:
                pass

    # Extract documentation files
    doc_files: Dict[str, str] = {}  # {path: content}
    for m in docs_tf.getmembers():
        if not m.isfile() or m.size > max_bytes:
            continue
        path = _strip_tar_leading_dir(m.name)

        ext = _ext(path)
        if ext in {".md", ".txt", ".rst"}:  # Documentation formats
            try:
                f = docs_tf.extractfile(m)
                if f:
                    content = f.read().decode('utf-8', errors='ignore')
                    doc_files[path] = content
            except Exception:
                pass

    # Perform cross-reference analysis
    analyzer = pattern_matching.CrossReferenceAnalyzer()
    cross_ref = analyzer.analyze_cross_references(code_files, doc_files)

    # Build summary
    entity_to_docs = cross_ref.get("entity_to_docs", {})
    references_by_doc = cross_ref.get("references_by_doc", {})

    # Find entities with most documentation
    entity_mention_counts = {}
    for entity, docs in entity_to_docs.items():
        total_mentions = 0
        for doc in docs:
            mentions = references_by_doc.get(doc, {}).get(entity, [])
            total_mentions += len(mentions)
        entity_mention_counts[entity] = {
            "docs": len(docs),
            "mentions": total_mentions,
            "doc_list": sorted(docs)
        }

    # Sort entities by documentation coverage
    top_documented = sorted(
        entity_mention_counts.items(),
        key=lambda x: (x[1]["docs"], x[1]["mentions"]),
        reverse=True
    )[:50]

    # Find undocumented entities
    all_entities = set(cross_ref.get("all_entities", []))
    documented_entities = set(entity_to_docs.keys())
    undocumented = sorted(all_entities - documented_entities)

    elapsed = time.monotonic() - start

    return {
        "code_ref": code_ref,
        "docs_ref": docs_ref,
        "total_entities": cross_ref["total_entities"],
        "total_code_files": len(code_files),
        "total_docs": len(doc_files),
        "documented_entities": len(documented_entities),
        "undocumented_entities": len(undocumented),
        "undocumented_list": undocumented[:20],
        "entity_to_docs": dict(list(entity_to_docs.items())[:50]),
        "top_documented": [
            {"entity": e, "docs": d["docs"], "mentions": d["mentions"]}
            for e, d in top_documented[:20]
        ],
        "cross_reference_details": {
            "references_by_doc": {
                doc: {entity: len(matches) for entity, matches in refs.items()}
                for doc, refs in list(references_by_doc.items())[:20]
            }
        },
        "elapsed_seconds": round(elapsed, 3),
    }
