from pathlib import Path

from video_storyboard.character_registry import CharacterRegistry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "examples" / "space-friends" / "characters"


def test_public_registry_is_valid() -> None:
    registry = CharacterRegistry.load(REGISTRY_DIR)
    assert registry.validate() == []
    assert {record.id for record in registry.records} == {"mio", "lux"}
    assert all(record.publishable for record in registry.records)
    assert all(record.asset_license for record in registry.records)


def test_alias_and_motion_selection() -> None:
    registry = CharacterRegistry.load(REGISTRY_DIR)
    records, unresolved = registry.resolve(["Mio", "ルクス"])
    assert unresolved == []

    motions = registry.select_motions(
        records,
        "cinematic-descentしながらルクスがinvitation pulseを見せる",
    )
    selected = {(motion.character_id, motion.motion_id) for motion in motions}
    assert ("mio", "design_presence") in selected
    assert ("mio", "cinematic_descent") in selected
    assert ("lux", "design_presence") in selected
    assert ("lux", "invitation_pulse") in selected
    assert all(motion.clip_path.is_file() for motion in motions)
