"""Skill scanning and loading for the Symbiont SDK.

Provides ClawHavoc-style security scanning and skill loading, ported from
the Rust runtime's skills/{scanner.rs, loader.rs} modules.
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import SkillLoadError

# =============================================================================
# Enums & Data Classes
# =============================================================================


class ScanSeverity(Enum):
    """Severity level for scan findings."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SignatureStatus(Enum):
    """Skill signature verification status."""

    VERIFIED = "verified"
    PINNED = "pinned"
    UNSIGNED = "unsigned"
    INVALID = "invalid"
    REVOKED = "revoked"


@dataclass
class ScanRule:
    """Base class for scan rules."""

    name: str
    pattern: str
    severity: ScanSeverity
    message: str


@dataclass
class ScanFinding:
    """A single finding from scanning."""

    rule: str
    severity: ScanSeverity
    message: str
    line: Optional[int] = None
    file: Optional[str] = None


@dataclass
class ScanResult:
    """Aggregated scan result."""

    passed: bool
    findings: List[ScanFinding] = field(default_factory=list)


@dataclass
class SignatureDetail:
    """Signature verification detail."""

    status: SignatureStatus
    domain: Optional[str] = None
    developer: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class SkillMetadata:
    """Metadata parsed from skill frontmatter."""

    name: str
    description: Optional[str] = None
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedSkill:
    """A fully loaded skill with content, metadata, and scan results."""

    name: str
    path: str
    signature_status: SignatureStatus
    content: str
    metadata: Optional[SkillMetadata] = None
    scan_result: Optional[ScanResult] = None


@dataclass
class SkillLoaderConfig:
    """Configuration for the skill loader."""

    load_paths: List[str] = field(default_factory=list)
    require_signed: bool = False
    allow_unsigned_from: List[str] = field(default_factory=list)
    auto_pin: bool = False
    scan_enabled: bool = True
    custom_deny_patterns: List[str] = field(default_factory=list)


# =============================================================================
# Default ClawHavoc Rules
# =============================================================================

_DEFAULT_RULES: List[ScanRule] = [
    ScanRule(
        name="pipe-to-shell",
        pattern=r"curl\s.*\|\s*(sh|bash|zsh)",
        severity=ScanSeverity.CRITICAL,
        message="Pipe to shell detected: remote code execution risk",
    ),
    ScanRule(
        name="wget-pipe-to-shell",
        pattern=r"wget\s.*\|\s*(sh|bash|zsh)",
        severity=ScanSeverity.CRITICAL,
        message="Wget pipe to shell detected: remote code execution risk",
    ),
    ScanRule(
        name="env-file-reference",
        pattern=r"\.(env|ENV)\b",
        severity=ScanSeverity.WARNING,
        message="Environment file reference detected: potential secret exposure",
    ),
    ScanRule(
        name="soul-md-modification",
        pattern=r"(write|modify|overwrite|replace).*SOUL\.md",
        severity=ScanSeverity.CRITICAL,
        message="SOUL.md modification detected: agent identity tampering",
    ),
    ScanRule(
        name="memory-md-modification",
        pattern=r"(write|modify|overwrite|replace).*memory\.md",
        severity=ScanSeverity.WARNING,
        message="memory.md modification detected: memory tampering risk",
    ),
    ScanRule(
        name="eval-with-fetch",
        pattern=r"eval\s*\(.*fetch",
        severity=ScanSeverity.CRITICAL,
        message="Eval with fetch detected: remote code execution risk",
    ),
    ScanRule(
        name="fetch-with-eval",
        pattern=r"fetch\s*\(.*\.then.*eval",
        severity=ScanSeverity.CRITICAL,
        message="Fetch-then-eval pattern detected: remote code execution risk",
    ),
    ScanRule(
        name="base64-decode-exec",
        pattern=r"(base64.*decode|atob)\s*\(.*\)\s*.*exec",
        severity=ScanSeverity.CRITICAL,
        message="Base64 decode with exec detected: obfuscated code execution",
    ),
    ScanRule(
        name="rm-rf-pattern",
        pattern=r"rm\s+-rf\s+/",
        severity=ScanSeverity.CRITICAL,
        message="Recursive force delete from root detected: destructive operation",
    ),
    ScanRule(
        name="chmod-777",
        pattern=r"chmod\s+777",
        severity=ScanSeverity.WARNING,
        message="chmod 777 detected: overly permissive file permissions",
    ),
]


# =============================================================================
# Skill Scanner
# =============================================================================


class SkillScanner:
    """Scans skill content for security issues using ClawHavoc rules."""

    def __init__(self, custom_rules: Optional[List[ScanRule]] = None) -> None:
        self._rules = list(_DEFAULT_RULES)
        if custom_rules:
            self._rules.extend(custom_rules)

    def scan_content(
        self, content: str, file_name: Optional[str] = None
    ) -> List[ScanFinding]:
        """Scan text content line-by-line against all rules."""
        findings: List[ScanFinding] = []
        for line_num, line in enumerate(content.splitlines(), start=1):
            for rule in self._rules:
                if re.search(rule.pattern, line):
                    findings.append(
                        ScanFinding(
                            rule=rule.name,
                            severity=rule.severity,
                            message=rule.message,
                            line=line_num,
                            file=file_name,
                        )
                    )
        return findings

    def scan_skill(self, skill_dir: str) -> ScanResult:
        """Walk a skill directory and scan all text files."""
        all_findings: List[ScanFinding] = []

        text_extensions = {
            ".md", ".txt", ".py", ".js", ".ts", ".sh",
            ".yaml", ".yml", ".json", ".toml",
        }

        for root, _dirs, files in os.walk(skill_dir):
            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext.lower() not in text_extensions:
                    continue

                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    findings = self.scan_content(content, file_name=fname)
                    all_findings.extend(findings)
                except OSError:
                    pass

        has_critical = any(
            f.severity == ScanSeverity.CRITICAL for f in all_findings
        )
        return ScanResult(passed=not has_critical, findings=all_findings)


# =============================================================================
# Skill Loader
# =============================================================================


def _parse_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter between ``---`` delimiters."""
    if not content.startswith("---"):
        return None

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None

    fm_text = content[3:end_idx].strip()
    if not fm_text:
        return None

    try:
        import yaml  # noqa: F811

        return yaml.safe_load(fm_text) or {}
    except Exception:
        return {}


class SkillLoader:
    """Loads skills from configured paths with optional scanning and verification."""

    def __init__(self, config: SkillLoaderConfig) -> None:
        self._config = config
        self._scanner = SkillScanner(
            custom_rules=[
                ScanRule(
                    name=f"custom-deny-{i}",
                    pattern=p,
                    severity=ScanSeverity.CRITICAL,
                    message=f"Custom deny pattern matched: {p}",
                )
                for i, p in enumerate(config.custom_deny_patterns)
            ]
            if config.custom_deny_patterns
            else None
        )
        self._schemapin_available = False
        try:
            from schemapin.verify import verify_schema_signature  # noqa: F401

            self._schemapin_available = True
        except ImportError:
            pass

    def load_all(self) -> List[LoadedSkill]:
        """Discover and load all skills from configured paths."""
        skills: List[LoadedSkill] = []
        for base_path in self._config.load_paths:
            if not os.path.isdir(base_path):
                continue
            for entry in sorted(os.listdir(base_path)):
                skill_dir = os.path.join(base_path, entry)
                skill_md = os.path.join(skill_dir, "SKILL.md")
                if os.path.isdir(skill_dir) and os.path.isfile(skill_md):
                    try:
                        skills.append(self.load_skill(skill_dir))
                    except SkillLoadError:
                        pass
        return skills

    def load_skill(self, path: str) -> LoadedSkill:
        """Load a single skill from a directory containing SKILL.md."""
        skill_md = os.path.join(path, "SKILL.md")
        if not os.path.isfile(skill_md):
            raise SkillLoadError(
                f"SKILL.md not found in {path}",
                skill_path=path,
            )

        try:
            with open(skill_md, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            raise SkillLoadError(
                f"Failed to read SKILL.md: {exc}",
                skill_path=path,
            ) from exc

        # Parse frontmatter for metadata
        metadata: Optional[SkillMetadata] = None
        fm = _parse_frontmatter(content)
        if fm is not None:
            metadata = SkillMetadata(
                name=fm.get("name", os.path.basename(path)),
                description=fm.get("description"),
                raw_frontmatter=fm,
            )

        name = metadata.name if metadata else os.path.basename(path)

        # Determine signature status
        sig_status = SignatureStatus.UNSIGNED
        if self._schemapin_available:
            sig_path = os.path.join(path, ".schemapin.sig")
            if os.path.isfile(sig_path):
                sig_status = SignatureStatus.PINNED
            # Full verification would require domain / key lookup
        else:
            sig_path = os.path.join(path, ".schemapin.sig")
            if os.path.isfile(sig_path):
                sig_status = SignatureStatus.PINNED

        # Scan if enabled
        scan_result: Optional[ScanResult] = None
        if self._config.scan_enabled:
            scan_result = self._scanner.scan_skill(path)

        return LoadedSkill(
            name=name,
            path=path,
            signature_status=sig_status,
            content=content,
            metadata=metadata,
            scan_result=scan_result,
        )
