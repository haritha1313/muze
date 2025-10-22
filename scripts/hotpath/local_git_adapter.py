"""
Local Git Adapter for Hot-Path Pipeline

Adapts the Hot-Path pipeline to work with local git repositories
instead of requiring GitHub API access.

This allows all 5 Hot-Path layers to run on local repos in CI/CD.
"""

import subprocess
import tarfile
import io
from typing import Optional, List, Dict
from pathlib import Path


def _run_git(*args, cwd: Optional[str] = None) -> bytes:
    """Run git command and return stdout as bytes"""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=True
    )
    return result.stdout


def get_local_repo_tarball(ref: str, repo_path: Optional[str] = None) -> bytes:
    """
    Get repository tarball at specific ref using local git.

    This is a drop-in replacement for _get_repo_tarball() that works
    with local git instead of GitHub API.

    Args:
        ref: Git reference (branch, tag, or commit SHA)
        repo_path: Path to git repository (defaults to current directory)

    Returns:
        Gzipped tar archive bytes
    """
    # Use git archive to create tarball
    tar_data = _run_git("archive", "--format=tar.gz", ref, cwd=repo_path)
    return tar_data


def list_local_repo_tree(ref: str, repo_path: Optional[str] = None) -> List[Dict]:
    """
    List all files in repo at specific ref using local git.

    Drop-in replacement for list_repo_tree() that works with local git.

    Args:
        ref: Git reference
        repo_path: Path to git repository

    Returns:
        List of dicts with file info (path, type, size, sha)
    """
    # Get list of files with: git ls-tree -r --long <ref>
    output = _run_git("ls-tree", "-r", "--long", ref, cwd=repo_path)

    tree = []
    for line in output.decode('utf-8').splitlines():
        if not line.strip():
            continue

        # Format: <mode> <type> <sha> <size> <path>
        # Example: 100644 blob abc123 1234 src/file.py
        parts = line.split(maxsplit=4)
        if len(parts) < 5:
            continue

        mode, obj_type, sha, size, path = parts

        # Convert size, handle '-' for directories
        try:
            file_size = int(size) if size != '-' else 0
        except ValueError:
            file_size = 0

        tree.append({
            "path": path,
            "type": obj_type,  # "blob" or "tree"
            "sha": sha,
            "size": file_size,
            "mode": mode
        })

    return tree


def get_local_commit_sha(ref: str, repo_path: Optional[str] = None) -> str:
    """
    Resolve ref to commit SHA using local git.

    Args:
        ref: Git reference (branch, tag, or commit)
        repo_path: Path to repository

    Returns:
        Full commit SHA
    """
    sha = _run_git("rev-parse", ref, cwd=repo_path)
    return sha.decode('utf-8').strip()


def get_local_default_branch(repo_path: Optional[str] = None) -> str:
    """
    Get default branch name from local git.

    Args:
        repo_path: Path to repository

    Returns:
        Default branch name (e.g., "main", "master")
    """
    # Get symbolic ref of HEAD
    try:
        ref = _run_git("symbolic-ref", "refs/remotes/origin/HEAD", cwd=repo_path)
        # Returns: refs/remotes/origin/main
        branch = ref.decode('utf-8').strip().split('/')[-1]
        return branch
    except subprocess.CalledProcessError:
        # Fallback: try common names
        for branch in ["main", "master"]:
            try:
                _run_git("rev-parse", "--verify", branch, cwd=repo_path)
                return branch
            except subprocess.CalledProcessError:
                continue
        raise RuntimeError("Could not determine default branch")


def find_repo_root(start_path: Optional[Path] = None) -> Path:
    """
    Find git repository root.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Path to repository root
    """
    current = (start_path or Path.cwd()).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not in a git repository")


class LocalGitAdapter:
    """
    Adapter to make Hot-Path pipeline work with local git.

    Usage:
        adapter = LocalGitAdapter()

        # Use with semantic analysis
        from pipeline import analyze_semantic_diff
        result = analyze_semantic_diff(
            api_base="local",  # Special marker
            token=None,
            code_slug=str(adapter.repo_path),
            old_ref="HEAD~1",
            new_ref="HEAD",
            settings=settings
        )
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize adapter.

        Args:
            repo_path: Path to repository (defaults to finding from cwd)
        """
        self.repo_path = repo_path or find_repo_root()

    def get_tarball(self, ref: str) -> bytes:
        """Get tarball for ref"""
        return get_local_repo_tarball(ref, str(self.repo_path))

    def list_tree(self, ref: str) -> List[Dict]:
        """List files at ref"""
        return list_local_repo_tree(ref, str(self.repo_path))

    def get_commit_sha(self, ref: str) -> str:
        """Resolve ref to SHA"""
        return get_local_commit_sha(ref, str(self.repo_path))

    def get_default_branch(self) -> str:
        """Get default branch name"""
        return get_local_default_branch(str(self.repo_path))


# Monkey-patch functions to make pipeline.py work with local git
def patch_pipeline_for_local_git(adapter: LocalGitAdapter):
    """
    Monkey-patch pipeline.py functions to use local git.

    Call this before using any pipeline functions:

        adapter = LocalGitAdapter()
        patch_pipeline_for_local_git(adapter)

        # Now pipeline functions work with local git
        result = analyze_semantic_diff(...)
    """
    import pipeline

    # Replace GitHub API functions with local git versions
    original_get_tarball = pipeline._get_repo_tarball
    original_list_tree = pipeline.list_repo_tree
    original_get_sha = pipeline._get_commit_sha
    original_get_branch = pipeline._get_default_branch

    def local_get_tarball(api_base, token, slug, ref):
        if api_base == "local":
            return adapter.get_tarball(ref)
        return original_get_tarball(api_base, token, slug, ref)

    def local_list_tree(api_base, token, slug, branch):
        if api_base == "local":
            return adapter.list_tree(branch)
        return original_list_tree(api_base, token, slug, branch)

    def local_get_sha(api_base, token, slug, branch):
        if api_base == "local":
            return adapter.get_commit_sha(branch)
        return original_get_sha(api_base, token, slug, branch)

    def local_get_branch(api_base, token, slug):
        if api_base == "local":
            return adapter.get_default_branch()
        return original_get_branch(api_base, token, slug)

    # Apply patches
    pipeline._get_repo_tarball = local_get_tarball
    pipeline.list_repo_tree = local_list_tree
    pipeline._get_commit_sha = local_get_sha
    pipeline._get_default_branch = local_get_branch


if __name__ == "__main__":
    """Test local git adapter"""
    print("Testing Local Git Adapter")
    print("=" * 80)

    try:
        adapter = LocalGitAdapter()
        print(f"[+] Found repository at: {adapter.repo_path}")

        # Test getting default branch
        branch = adapter.get_default_branch()
        print(f"[+] Default branch: {branch}")

        # Test resolving ref
        sha = adapter.get_commit_sha("HEAD")
        print(f"[+] HEAD resolves to: {sha[:8]}")

        # Test listing tree
        tree = adapter.list_tree("HEAD")
        print(f"[+] Found {len(tree)} files at HEAD")

        # Test getting tarball
        tarball = adapter.get_tarball("HEAD")
        print(f"[+] Generated tarball: {len(tarball)} bytes")

        # Verify tarball is valid
        tf = tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz")
        members = tf.getmembers()
        print(f"[+] Tarball contains {len(members)} files")

        print("\n" + "=" * 80)
        print("[PASS] All tests passed! Local git adapter is working.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
