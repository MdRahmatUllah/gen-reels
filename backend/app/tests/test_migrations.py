from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_and_downgrade(tmp_path: Path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    backend_dir = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)

    command.upgrade(alembic_cfg, "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()
    assert "render_jobs" in inspector.get_table_names()
    assert "scene_plans" in inspector.get_table_names()
    assert "scene_segments" in inspector.get_table_names()
    assert "visual_presets" in inspector.get_table_names()
    assert "voice_presets" in inspector.get_table_names()
    assert "assets" in inspector.get_table_names()
    assert "asset_variants" in inspector.get_table_names()
    assert "exports" in inspector.get_table_names()
    assert "subscriptions" in inspector.get_table_names()
    assert "credit_ledger_entries" in inspector.get_table_names()
    assert "project_templates" in inspector.get_table_names()
    assert "template_versions" in inspector.get_table_names()
    assert "prompt_history_entries" in inspector.get_table_names()

    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()
