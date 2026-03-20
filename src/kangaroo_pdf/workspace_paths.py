from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    generated_root: Path
    source_dir: Path
    release_dir: Path
    data_dir: Path
    review_dir: Path
    text_report_dir: Path
    answer_compare_dir: Path
    asset_qa_dir: Path
    cache_dir: Path
    cleanup_report_path: Path


def workspace_paths(root: Path | str | None = None) -> WorkspacePaths:
    workspace_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    generated_root = workspace_root / ".generated"
    reports_root = generated_root / "reports"
    return WorkspacePaths(
        root=workspace_root,
        generated_root=generated_root,
        source_dir=workspace_root / "original_pdf_data",
        release_dir=workspace_root / "release-data",
        data_dir=generated_root / "data",
        review_dir=generated_root / "review-data" / "text-verification",
        text_report_dir=reports_root / "text-diff",
        answer_compare_dir=reports_root / "answer-compare",
        asset_qa_dir=reports_root / "asset-qa",
        cache_dir=generated_root / "cache",
        cleanup_report_path=reports_root / "release-cleanup-allowlist.json",
    )


def workspace_root_for_data_dir(data_dir: Path | str) -> Path:
    data_path = Path(data_dir).resolve()
    if data_path.parent.name == ".generated":
        return data_path.parent.parent.resolve()
    return data_path.parent.resolve()
