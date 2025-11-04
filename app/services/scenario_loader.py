from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy import delete
from sqlmodel import Session, select

from app.models_scenarios import InteropScenario, InteropScenarioStep


def parse_hl7_messages(content: str) -> List[str]:
    """Split an HL7 batch string into individual messages (using MSH as delimiter)."""
    messages: List[str] = []
    current: List[str] = []

    for line in content.splitlines():
        if line.startswith("MSH|"):
            if current:
                messages.append("\n".join(current).strip())
                current = []
        if line.strip() == "" and current:
            # blank line separates messages in many test files – finalize current message
            messages.append("\n".join(current).strip())
            current = []
            continue
        if line or current:
            current.append(line.rstrip("\r"))

    if current:
        messages.append("\n".join(current).strip())

    return [msg for msg in messages if msg]


def find_msh_type(message: str) -> Optional[str]:
    line = message.split("\n", 1)[0]
    parts = line.split("|")
    if len(parts) > 8:
        return parts[8]
    return None


def scenario_key_from_path(base_dir: Path, file_path: Path) -> str:
    rel = file_path.relative_to(base_dir)
    return str(rel).replace("\\", "/")


def load_hl7_files(
    session: Session,
    base_dir: Path,
    files: Iterable[Path],
    *,
    default_category: Optional[str] = None,
    ght_context_id: Optional[int] = None,
    tag_prefix: Optional[str] = None,
) -> int:
    """Load HL7 scenario files into the database."""
    created_or_updated = 0

    for hl7_file in files:
        content = hl7_file.read_text(encoding="utf-8", errors="ignore")
        messages = parse_hl7_messages(content)
        if not messages:
            continue

        key = scenario_key_from_path(base_dir, hl7_file)
        name = hl7_file.stem.replace("_", " ")
        parts = key.split("/")
        category = default_category or (parts[0] if len(parts) > 1 else None)
        tags: List[str] = []
        if tag_prefix:
            tags.append(tag_prefix)
        parent_name = hl7_file.parent.name
        if parent_name and parent_name != parts[0]:
            tags.append(parent_name)
        tags_value = ",".join(dict.fromkeys(tags)) if tags else None

        scenario = session.exec(select(InteropScenario).where(InteropScenario.key == key)).first()
        if scenario is None:
            scenario = InteropScenario(
                key=key,
                name=name,
                description=f"Importé depuis {hl7_file}",
                category=category,
                protocol="HL7",
                source_path=str(hl7_file),
                tags=tags_value,
                ght_context_id=ght_context_id,
            )
            session.add(scenario)
            session.flush()
        else:
            scenario.name = name
            scenario.category = category or scenario.category
            scenario.source_path = str(hl7_file)
            scenario.protocol = "HL7"
            scenario.ght_context_id = ght_context_id or scenario.ght_context_id
            scenario.tags = tags_value or scenario.tags
            scenario.updated_at = datetime.utcnow()

        # Replace existing steps
        session.exec(delete(InteropScenarioStep).where(InteropScenarioStep.scenario_id == scenario.id))
        session.flush()

        steps = []
        for idx, msg in enumerate(messages, start=1):
            message_type = find_msh_type(msg)
            steps.append(
                InteropScenarioStep(
                    scenario_id=scenario.id,
                    order_index=idx,
                    name=message_type or f"Message {idx}",
                    message_format="hl7",
                    message_type=message_type,
                    payload=msg,
                )
            )
        session.add_all(steps)
        created_or_updated += 1

    session.commit()
    return created_or_updated


def discover_hl7_files(base_dir: Path, patterns: Optional[List[str]] = None) -> List[Path]:
    """Return a sorted list of HL7 files under base_dir matching optional glob patterns."""
    if not base_dir.exists():
        return []

    if patterns:
        files: List[Path] = []
        for pattern in patterns:
            files.extend(sorted(base_dir.glob(pattern)))
    else:
        files = sorted(base_dir.rglob("*.hl7"))

    return [f for f in files if f.is_file()]
