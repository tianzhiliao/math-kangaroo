from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable

from PIL import Image

from .workspace_paths import workspace_root_for_data_dir

MANUAL_ASSET_SOURCE = "manual_crops_applied"
PNG_MEDIA_TYPE = "image/png"
RELEASE_SCHEMA_VERSION = 1

MANIFEST_KEYS = {"schema_version", "generated_at", "exams"}
MANIFEST_EXAM_KEYS = {
    "asset_count",
    "exam_id",
    "family",
    "language",
    "level",
    "path",
    "question_count",
    "year",
}
EXAM_KEYS = {
    "answer_key",
    "assets",
    "duration_minutes",
    "exam_id",
    "family",
    "instructions",
    "language",
    "level",
    "question_count",
    "questions",
    "scoring_rules",
    "year",
}
ASSET_KEYS = {"format", "height", "id", "kind", "media_type", "path", "role", "width"}
QUESTION_KEYS = {"choices", "id", "number", "part", "points", "shared_asset_refs", "stem_text"}
CHOICE_KEYS = {"asset_refs", "label", "text"}

BANNED_JSON_TOKENS = (
    ".html",
    ".pdf",
    ".svg",
    "asset_source",
    "legacy_auto_",
    "manual_crop_ref",
    "original_pdf_data",
    "qa_review_ref",
    "reports",
    "review-data",
    "source_audit_ref",
    "source_pdf",
)
LEGACY_CLEANUP_DIRS = ("data", "review-data", "reports", "tmp")
PROTECTED_SIBLING_DIRS = ("original_pdf_data", "release-data")


class ReleaseDataValidationError(ValueError):
    pass


def build_cleanup_allowlist_report(
    data_dir: Path | str,
    report_path: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    data_path = Path(data_dir).resolve()
    repo_root = workspace_root_for_data_dir(data_path)
    manifest = _read_json(data_path / "manifest.json")
    exam_entries = _select_exam_entries(manifest, exam_ids)

    release_input_files = _collect_release_input_files(data_path, exam_entries)
    cleanup_roots = _cleanup_roots(data_path, repo_root)
    protected_roots = [repo_root / dirname for dirname in PROTECTED_SIBLING_DIRS if (repo_root / dirname).exists()]
    delete_candidates = [
        path
        for path in _collect_files(cleanup_roots)
        if not any(_path_is_within(path, protected_root) for protected_root in protected_roots)
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": data_path.as_posix(),
        "selected_exam_ids": [entry["exam_id"] for entry in exam_entries],
        "cleanup_roots": [_display_path(path, repo_root) for path in cleanup_roots],
        "release_input_files": [_file_record(path, repo_root) for path in release_input_files],
        "delete_candidates": [_file_record(path, repo_root) for path in delete_candidates],
        "summary": {
            "release_input_count": len(release_input_files),
            "release_input_bytes": sum(path.stat().st_size for path in release_input_files),
            "delete_candidate_count": len(delete_candidates),
            "delete_candidate_bytes": sum(path.stat().st_size for path in delete_candidates),
        },
    }
    _write_json(Path(report_path), payload)
    return payload


def build_release_dataset(
    data_dir: Path | str,
    output_dir: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    data_path = Path(data_dir).resolve()
    output_path = Path(output_dir).resolve()
    manifest = _read_json(data_path / "manifest.json")
    exam_entries = _select_exam_entries(manifest, exam_ids)

    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    release_entries: list[dict[str, Any]] = []
    for entry in exam_entries:
        release_entries.append(_build_release_exam(data_path, output_path, entry["exam_id"]))

    release_manifest = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exams": release_entries,
    }
    _write_json(output_path / "manifest.json", release_manifest)
    return release_manifest


def validate_release_dataset(
    output_dir: Path | str,
    *,
    exam_ids: list[str] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    manifest_path = output_path / "manifest.json"
    manifest = _read_json(manifest_path)

    _validate_exact_keys(manifest, MANIFEST_KEYS, "manifest.json")
    if manifest.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise ReleaseDataValidationError(
            f"manifest.json schema_version must be {RELEASE_SCHEMA_VERSION}, got {manifest.get('schema_version')!r}"
        )
    _assert_no_absolute_paths(manifest, manifest_path)
    _assert_no_banned_tokens(manifest, manifest_path)

    exam_entries = _select_exam_entries(manifest, exam_ids)
    invalid_files = [
        path.relative_to(output_path).as_posix()
        for path in output_path.rglob("*")
        if path.is_file() and path.suffix.lower() not in {".json", ".png"}
    ]
    if invalid_files:
        raise ReleaseDataValidationError(f"release-data contains unsupported files: {invalid_files}")

    total_asset_count = 0
    for entry in exam_entries:
        total_asset_count += _validate_release_exam(output_path, entry)

    return {
        "release_dir": output_path.as_posix(),
        "exam_count": len(exam_entries),
        "asset_count": total_asset_count,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def ordered_referenced_asset_ids(exam_json: dict[str, Any]) -> list[str]:
    ordered_ids: list[str] = []
    seen: set[str] = set()

    def add(asset_id: str) -> None:
        if asset_id not in seen:
            ordered_ids.append(asset_id)
            seen.add(asset_id)

    for question in exam_json.get("questions", []):
        for asset_id in question.get("shared_asset_refs", []):
            add(str(asset_id))
        for choice in question.get("choices", []):
            for asset_id in choice.get("asset_refs", []):
                add(str(asset_id))
    return ordered_ids


def _build_release_exam(data_path: Path, output_path: Path, exam_id: str) -> dict[str, Any]:
    source_exam_dir = data_path / "exams" / exam_id
    source_exam = _read_json(source_exam_dir / "exam.json")
    if source_exam.get("asset_source") != MANUAL_ASSET_SOURCE:
        raise ReleaseDataValidationError(
            f"Exam {exam_id} is not ready for PNG release; expected asset_source={MANUAL_ASSET_SOURCE!r}."
        )

    referenced_asset_ids = ordered_referenced_asset_ids(source_exam)
    asset_lookup = {asset["id"]: asset for asset in source_exam.get("assets", [])}
    missing_assets = [asset_id for asset_id in referenced_asset_ids if asset_id not in asset_lookup]
    if missing_assets:
        raise ReleaseDataValidationError(f"Exam {exam_id} is missing asset records for: {', '.join(missing_assets)}")

    release_exam_dir = output_path / "exams" / exam_id
    release_assets_dir = release_exam_dir / "assets"
    release_assets_dir.mkdir(parents=True, exist_ok=True)

    release_assets = [
        _build_release_asset(
            exam_id=exam_id,
            source_exam_dir=source_exam_dir,
            release_assets_dir=release_assets_dir,
            source_asset=asset_lookup[asset_id],
        )
        for asset_id in referenced_asset_ids
    ]

    release_exam = {
        "exam_id": source_exam["exam_id"],
        "year": source_exam.get("year"),
        "family": source_exam.get("family"),
        "level": source_exam.get("level"),
        "language": source_exam.get("language"),
        "duration_minutes": source_exam.get("duration_minutes"),
        "question_count": source_exam.get("question_count"),
        "scoring_rules": list(source_exam.get("scoring_rules", [])),
        "instructions": list(source_exam.get("instructions", [])),
        "answer_key": dict(source_exam.get("answer_key", {})),
        "assets": release_assets,
        "questions": [_build_release_question(question) for question in source_exam.get("questions", [])],
    }
    _write_json(release_exam_dir / "exam.json", release_exam)
    return {
        "exam_id": exam_id,
        "path": f"exams/{exam_id}/exam.json",
        "family": release_exam["family"],
        "year": release_exam["year"],
        "level": release_exam["level"],
        "language": release_exam["language"],
        "question_count": len(release_exam["questions"]),
        "asset_count": len(release_assets),
    }


def _build_release_question(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": question["id"],
        "number": question["number"],
        "part": question.get("part"),
        "points": question.get("points"),
        "stem_text": question.get("stem_text", ""),
        "choices": [
            {
                "label": choice["label"],
                "text": choice.get("text", ""),
                "asset_refs": list(choice.get("asset_refs", [])),
            }
            for choice in question.get("choices", [])
        ],
        "shared_asset_refs": list(question.get("shared_asset_refs", [])),
    }


def _build_release_asset(
    *,
    exam_id: str,
    source_exam_dir: Path,
    release_assets_dir: Path,
    source_asset: dict[str, Any],
) -> dict[str, Any]:
    source_path = _resolve_source_asset_path(exam_id, source_exam_dir, source_asset)
    release_filename = source_path.name
    release_path = release_assets_dir / release_filename
    shutil.copy2(source_path, release_path)

    width, height = _read_image_size(release_path)
    return {
        "id": source_asset["id"],
        "path": f"assets/{release_filename}",
        "format": "png",
        "media_type": PNG_MEDIA_TYPE,
        "kind": source_asset.get("kind", "question_figure"),
        "role": source_asset.get("role", ""),
        "width": width,
        "height": height,
    }


def _validate_release_exam(output_path: Path, entry: dict[str, Any]) -> int:
    exam_id = entry.get("exam_id")
    _validate_exact_keys(entry, MANIFEST_EXAM_KEYS, f"manifest entry {exam_id}")
    exam_rel_path = _ensure_relative_path(str(entry["path"]), f"manifest entry {exam_id} path")
    exam_path = _resolve_relative_path(output_path, exam_rel_path, f"manifest entry {exam_id} path")
    if not exam_path.exists():
        raise ReleaseDataValidationError(f"Missing release exam file: {exam_rel_path}")

    exam_payload = _read_json(exam_path)
    _validate_exact_keys(exam_payload, EXAM_KEYS, exam_rel_path)
    _assert_no_absolute_paths(exam_payload, exam_path)
    _assert_no_banned_tokens(exam_payload, exam_path)

    if exam_payload["exam_id"] != exam_id:
        raise ReleaseDataValidationError(
            f"Exam payload id mismatch for {exam_rel_path}: {exam_payload['exam_id']!r} != {exam_id!r}"
        )
    if entry["question_count"] != len(exam_payload["questions"]):
        raise ReleaseDataValidationError(f"Manifest question_count mismatch for {exam_id}")
    if entry["asset_count"] != len(exam_payload["assets"]):
        raise ReleaseDataValidationError(f"Manifest asset_count mismatch for {exam_id}")
    if exam_payload["question_count"] != len(exam_payload["questions"]):
        raise ReleaseDataValidationError(f"Exam {exam_id} question_count does not match questions length")
    if len(exam_payload["answer_key"]) != len(exam_payload["questions"]):
        raise ReleaseDataValidationError(f"Exam {exam_id} answer_key length does not match questions length")

    asset_lookup = {asset["id"]: asset for asset in exam_payload["assets"]}
    referenced_asset_ids = ordered_referenced_asset_ids(exam_payload)
    missing_assets = [asset_id for asset_id in referenced_asset_ids if asset_id not in asset_lookup]
    if missing_assets:
        raise ReleaseDataValidationError(f"Exam {exam_id} is missing referenced assets: {missing_assets}")
    unused_assets = sorted(set(asset_lookup) - set(referenced_asset_ids))
    if unused_assets:
        raise ReleaseDataValidationError(f"Exam {exam_id} contains unreferenced assets: {unused_assets}")

    for question in exam_payload["questions"]:
        _validate_exact_keys(question, QUESTION_KEYS, f"{exam_rel_path} question {question.get('id')}")
        for choice in question["choices"]:
            _validate_exact_keys(choice, CHOICE_KEYS, f"{exam_rel_path} choice {choice.get('label')}")

    expected_asset_paths: set[str] = set()
    for asset in exam_payload["assets"]:
        _validate_exact_keys(asset, ASSET_KEYS, f"{exam_rel_path} asset {asset.get('id')}")
        if asset["format"] != "png":
            raise ReleaseDataValidationError(f"Exam {exam_id} asset {asset['id']} must be png, got {asset['format']!r}")
        if asset["media_type"] != PNG_MEDIA_TYPE:
            raise ReleaseDataValidationError(
                f"Exam {exam_id} asset {asset['id']} must be {PNG_MEDIA_TYPE!r}, got {asset['media_type']!r}"
            )
        asset_rel_path = _ensure_relative_path(asset["path"], f"{exam_rel_path} asset {asset['id']} path")
        asset_path = _resolve_relative_path(exam_path.parent, asset_rel_path, f"{exam_rel_path} asset {asset['id']} path")
        if asset_path.suffix.lower() != ".png":
            raise ReleaseDataValidationError(f"Exam {exam_id} asset {asset['id']} path must end with .png")
        if not asset_path.exists():
            raise ReleaseDataValidationError(f"Missing asset file for {exam_id}:{asset['id']} at {asset_rel_path}")
        width, height = _read_image_size(asset_path)
        if asset["width"] != width or asset["height"] != height:
            raise ReleaseDataValidationError(
                f"Exam {exam_id} asset {asset['id']} dimensions do not match file contents: "
                f"{asset['width']}x{asset['height']} != {width}x{height}"
            )
        expected_asset_paths.add(asset_rel_path)

    assets_dir = exam_path.parent / "assets"
    actual_asset_paths = {
        path.relative_to(exam_path.parent).as_posix()
        for path in assets_dir.rglob("*")
        if path.is_file()
    }
    if actual_asset_paths != expected_asset_paths:
        raise ReleaseDataValidationError(
            f"Exam {exam_id} asset file set mismatch: expected {sorted(expected_asset_paths)}, got {sorted(actual_asset_paths)}"
        )

    return len(exam_payload["assets"])


def _collect_release_input_files(data_path: Path, exam_entries: list[dict[str, Any]]) -> list[Path]:
    release_inputs = {data_path / "manifest.json"}
    for entry in exam_entries:
        exam_dir = data_path / "exams" / entry["exam_id"]
        exam_json_path = exam_dir / "exam.json"
        source_exam = _read_json(exam_json_path)
        release_inputs.add(exam_json_path)
        asset_lookup = {asset["id"]: asset for asset in source_exam.get("assets", [])}
        for asset_id in ordered_referenced_asset_ids(source_exam):
            if asset_id not in asset_lookup:
                raise ReleaseDataValidationError(
                    f"Exam {entry['exam_id']} is missing asset records for allowlist generation: {asset_id}"
                )
            release_inputs.add(_resolve_source_asset_path(entry["exam_id"], exam_dir, asset_lookup[asset_id]))
    return sorted(path.resolve() for path in release_inputs)


def _resolve_source_asset_path(exam_id: str, source_exam_dir: Path, source_asset: dict[str, Any]) -> Path:
    asset_rel_path = _ensure_relative_path(str(source_asset["path"]), f"source asset path for {exam_id}:{source_asset['id']}")
    source_path = _resolve_relative_path(source_exam_dir, asset_rel_path, f"source asset path for {exam_id}:{source_asset['id']}")
    if source_asset.get("format") != "png" or source_path.suffix.lower() != ".png":
        raise ReleaseDataValidationError(f"Exam {exam_id} asset {source_asset['id']} must reference a PNG file")
    if not source_path.exists():
        raise ReleaseDataValidationError(f"Missing source asset for {exam_id}:{source_asset['id']} at {asset_rel_path}")
    return source_path


def _read_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        width, height = image.size
    return int(width), int(height)


def _select_exam_entries(manifest: dict[str, Any], exam_ids: list[str] | None) -> list[dict[str, Any]]:
    selected_exam_ids = set(exam_ids or [])
    exam_entries = [
        entry
        for entry in manifest.get("exams", [])
        if not selected_exam_ids or entry.get("exam_id") in selected_exam_ids
    ]
    if selected_exam_ids:
        known_exam_ids = {entry.get("exam_id") for entry in manifest.get("exams", [])}
        missing_exam_ids = sorted(selected_exam_ids - known_exam_ids)
        if missing_exam_ids:
            raise ReleaseDataValidationError(f"Unknown exam_id values: {', '.join(missing_exam_ids)}")
    if not exam_entries:
        raise ReleaseDataValidationError("No exams matched the requested release build scope.")
    return exam_entries


def _collect_files(roots: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root.resolve())
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                files.append(path.resolve())
    return sorted(files)


def _cleanup_roots(data_path: Path, repo_root: Path) -> list[Path]:
    generated_root = repo_root / ".generated"
    roots: list[Path] = []

    if _path_is_within(data_path, generated_root):
        if generated_root.exists():
            roots.append(generated_root)
    else:
        roots.append(data_path)

    for dirname in LEGACY_CLEANUP_DIRS:
        candidate = repo_root / dirname
        if candidate.exists():
            roots.append(candidate)

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_roots.append(resolved)
    return unique_roots


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file_record(path: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "path": _display_path(path, repo_root),
        "size_bytes": path.stat().st_size,
    }


def _ensure_relative_path(value: str, label: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ReleaseDataValidationError(f"{label} must not be empty")
    if _looks_like_absolute_path(candidate):
        raise ReleaseDataValidationError(f"{label} must be relative, got {candidate!r}")
    normalized = Path(candidate).as_posix()
    if normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        raise ReleaseDataValidationError(f"{label} must stay within the dataset, got {candidate!r}")
    return normalized


def _resolve_relative_path(base_dir: Path, relative_path: str, label: str) -> Path:
    resolved = (base_dir / relative_path).resolve()
    try:
        resolved.relative_to(base_dir.resolve())
    except ValueError as exc:
        raise ReleaseDataValidationError(f"{label} escapes the dataset root: {relative_path!r}") from exc
    return resolved


def _looks_like_absolute_path(value: str) -> bool:
    return value.startswith("/") or Path(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _assert_no_absolute_paths(payload: Any, source_path: Path) -> None:
    for value in _iter_strings(payload):
        if _looks_like_absolute_path(value):
            raise ReleaseDataValidationError(f"{source_path.as_posix()} contains an absolute path: {value!r}")


def _assert_no_banned_tokens(payload: Any, source_path: Path) -> None:
    strings = [value.lower() for value in _iter_strings(payload)]
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    for token in BANNED_JSON_TOKENS:
        lowered = token.lower()
        if lowered in text or any(lowered in value for value in strings):
            raise ReleaseDataValidationError(f"{source_path.as_posix()} contains banned token {token!r}")


def _iter_strings(payload: Any) -> Iterable[str]:
    if isinstance(payload, str):
        yield payload
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key)
            yield from _iter_strings(value)
        return
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_strings(item)


def _validate_exact_keys(payload: dict[str, Any], expected_keys: set[str], label: str) -> None:
    actual_keys = set(payload.keys())
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ReleaseDataValidationError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
