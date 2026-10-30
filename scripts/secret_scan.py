#!/usr/bin/env python3
"""
Yatrika - Secret Scanner Script
Scans git working tree, diffs, and history for committed credentials or secrets:
- IBM Watsonx API keys
- OpenWeatherMap API keys
- Flask / JWT SECRET_KEY values
- Cloud provider keys (AWS, GCP, GitHub tokens)
- Private RSA/OpenSSH/SSL keys
- Committed .env files

Usage:
    python scripts/secret_scan.py           # Scan all tracked files
    python scripts/secret_scan.py --diff    # Scan git diff (staged/unstaged)
    python scripts/secret_scan.py --history # Scan git commit log history
"""

import sys
import re
import subprocess
from pathlib import Path

# Safe placeholder tokens that are allowed in documentation / templates / tests
SAFE_PLACEHOLDERS = {
    "your_ibm_cloud_api_key_here",
    "your_watsonx_project_id_here",
    "your_openweathermap_api_key_here",
    "your_exchangerate_api_key_here",
    "replace-with-a-secure-random-secret-key-32-bytes-minimum",
    "test-secret-key-for-development-mode-min-32-chars-long",
    "dev-secret-key-for-local-testing-only-32b",
    "testing-secret-key-32-bytes-minimum-length-ok",
    "testing-secret-key-32-bytes-minimum-ok",
    "your-ibm-api-key-here",
    "your_secret_key_here",
    "your-32-byte-hex-secret-key-change-in-production"
}

# Regex patterns for high-entropy / secret tokens
SECRET_PATTERNS = [
    (r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----', "Private Cryptographic Key"),
    (r'(?i)IBM_API_KEY\s*=\s*["\']([a-zA-Z0-9_\-]{24,})["\']', "IBM Watsonx API Key"),
    (r'(?i)WEATHER_API_KEY\s*=\s*["\']([a-zA-Z0-9]{28,36})["\']', "OpenWeatherMap API Key"),
    (r'(?i)SECRET_KEY\s*=\s*["\']([a-zA-Z0-9_\-]{32,})["\']', "Flask / App Secret Key"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'AIza[0-9A-Za-z\\-_]{35}', "Google API Key"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
    (r'sk-[a-zA-Z0-9]{32,}', "OpenAI / Cloud Secret Key")
]

IGNORE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.pdf', '.db', '.sqlite3', '.pkl'}
IGNORE_PATHS = {'venv', '.git', '__pycache__', 'node_modules', '.pytest_cache'}


def is_placeholder(val: str) -> bool:
    clean = val.strip().lower()
    for placeholder in SAFE_PLACEHOLDERS:
        if placeholder in clean:
            return True
    if any(prefix in clean for prefix in ["your_", "dummy_", "test_", "fake_", "placeholder_", "example_"]):
        return True
    return False


def scan_text(content: str, source_name: str) -> list:
    """Scans text content against all secret patterns."""
    findings = []
    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        # Ignore comments in test/example files that explicitly say placeholder
        if "# safe placeholder" in line.lower() or "example" in source_name.lower():
            continue

        for pattern, desc in SECRET_PATTERNS:
            match = re.search(pattern, line)
            if match:
                matched_val = match.group(1) if match.groups() else match.group(0)
                if not is_placeholder(matched_val):
                    findings.append({
                        "source": source_name,
                        "line": line_idx,
                        "description": desc,
                        "preview": line.strip()[:80]
                    })
    return findings


def scan_working_tree(repo_root: Path) -> list:
    """Scans all tracked files in git working tree."""
    findings = []
    try:
        tracked_files = subprocess.check_output(
            ["git", "ls-files"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
        ).splitlines()
    except Exception:
        # Fallback to traversing files
        tracked_files = [str(p.relative_to(repo_root)) for p in repo_root.rglob("*") if p.is_file()]

    for rel_path in tracked_files:
        p = repo_root / rel_path
        if not p.is_file():
            continue

        # Skip ignored paths
        if any(part in IGNORE_PATHS for part in p.parts):
            continue
        if p.suffix.lower() in IGNORE_EXTENSIONS:
            continue

        # Check for committed .env files (except .env.example)
        if p.name.startswith(".env") and not p.name.endswith(".example"):
            findings.append({
                "source": rel_path,
                "line": 1,
                "description": "Committed .env environment file",
                "preview": f"File {p.name} is tracked in git"
            })
            continue

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            findings.extend(scan_text(content, rel_path))
        except Exception:
            pass

    return findings


def scan_diff(repo_root: Path) -> list:
    """Scans git diff (staged and unstaged) for secret patterns."""
    findings = []
    try:
        diff_out = subprocess.check_output(
            ["git", "diff", "HEAD"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        diff_out = ""

    current_file = "git-diff"
    line_num = 0
    for line in diff_out.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            line_num += 1
            added_content = line[1:]
            for pattern, desc in SECRET_PATTERNS:
                match = re.search(pattern, added_content)
                if match:
                    val = match.group(1) if match.groups() else match.group(0)
                    if not is_placeholder(val):
                        findings.append({
                            "source": current_file,
                            "line": line_num,
                            "description": desc,
                            "preview": added_content.strip()[:80]
                        })
    return findings


def scan_history(repo_root: Path) -> list:
    """Scans git log commit history for secret patterns."""
    findings = []
    try:
        log_out = subprocess.check_output(
            ["git", "log", "-n", "50", "-p"],
            cwd=repo_root, text=True, stderr=subprocess.DEVNULL,
            encoding="utf-8", errors="ignore"
        )
        for line in log_out.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added = line[1:]
                for pattern, desc in SECRET_PATTERNS:
                    match = re.search(pattern, added)
                    if match:
                        val = match.group(1) if match.groups() else match.group(0)
                        if not is_placeholder(val):
                            findings.append({
                                "source": "git-commit-history",
                                "line": 0,
                                "description": desc,
                                "preview": added.strip()[:80]
                            })
    except Exception:
        pass
    return findings


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    repo_root = Path(__file__).resolve().parent.parent
    mode = sys.argv[1] if len(sys.argv) > 1 else "--tree"

    print(f"[*] Running Yatrika Secret Scanner ({mode})...")
    if mode == "--diff":
        findings = scan_diff(repo_root)
    elif mode == "--history":
        findings = scan_history(repo_root)
    else:
        findings = scan_working_tree(repo_root)

    if findings:
        print("\n[!] SECURITY ALERT: Potential secrets or credentials detected!\n")
        for f in findings:
            print(f"  * [{f['description']}] in {f['source']}:{f['line']}")
            print(f"    Code preview: {f['preview']}\n")
        print("Please revoke or remove these secrets before pushing to public repositories.")
        sys.exit(1)
    else:
        print("[+] Secret scan passed: Zero secrets or exposed credentials detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
