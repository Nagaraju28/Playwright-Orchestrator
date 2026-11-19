import os
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

class IngestionService:
    """Handles Git repository cloning and Zip archive extraction for projects."""

    @staticmethod
    def format_authenticated_git_url(git_url: str, pat: Optional[str]) -> str:
        """Inject personal access token into HTTPS Git clone URL securely."""
        if not pat or not git_url.startswith("http"):
            return git_url
        
        parsed = urlparse(git_url)
        # Reconstruct with oauth2:<PAT>@domain
        netloc = f"oauth2:{pat}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))

    @classmethod
    def clone_git_repository(
        cls,
        git_url: str,
        target_dir: Path,
        branch: str = "main",
        pat: Optional[str] = None,
        depth: int = 1,
    ) -> bool:
        """Clone a remote Git repository to target directory."""
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        auth_url = cls.format_authenticated_git_url(git_url, pat)
        cmd = [
            "git",
            "clone",
            "--depth", str(depth),
            "--branch", branch,
            auth_url,
            str(target_dir),
        ]

        # Hide token from exception traces
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            if res.returncode != 0:
                clean_err = res.stderr.replace(pat or "____", "********") if pat else res.stderr
                raise RuntimeError(f"Git clone failed (exit {res.returncode}): {clean_err.strip()}")
            return True
        except subprocess.TimeoutExpired:
            raise TimeoutError("Git clone timed out after 120 seconds")

    @classmethod
    def extract_zip_bundle(cls, zip_path: Path, target_dir: Path) -> int:
        """Extract a zip archive workspace bundle into target directory."""
        if not zip_path.exists():
            raise FileNotFoundError(f"Zip archive not found: {zip_path}")
        
        target_dir.mkdir(parents=True, exist_ok=True)
        extracted_count = 0
        with zipfile.ZipFile(zip_path, "r") as archive:
            # Prevent zip-slip vulnerability
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    continue  # Skip dangerous relative paths
                archive.extract(member, target_dir)
                extracted_count += 1
        return extracted_count
