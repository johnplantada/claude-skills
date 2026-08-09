"""Guards over lifecycle skill separation and mutation authority."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "plugins" / "digital-twin" / "skills"


def skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def test_router_names_each_primary_skill_and_has_no_mutation_helpers():
    router = skill_text("digital-twin")
    for name in ("build-digital-twin", "use-career-twin", "maintain-digital-twin"):
        assert name in router
    assert not (SKILLS / "digital-twin" / "scripts").exists()
    assert "never reads owner sources, answers from the twin, or mutates bundle state" in router


def test_private_use_is_snapshot_only_and_routes_factual_changes_to_maintenance():
    private_use = skill_text("use-career-twin")
    assert "current compiled private snapshot as the only factual answer source" in private_use
    assert "must not edit claims" in private_use
    assert "maintain-digital-twin" in private_use
    assert "career_twin.py feedback" in private_use


def test_maintenance_is_the_only_update_path_and_blocks_stale_serving():
    maintenance = skill_text("maintain-digital-twin")
    assert (
        "sole deterministic mutation step"
        in (SKILLS / "maintain-digital-twin" / "references" / "update-transaction.md").read_text()
    )
    assert "Block private serving" in maintenance
    assert "update_bundle.py plan" in maintenance
    assert "migrate_workspace.py" in maintenance
