from __future__ import annotations

import argparse
import re
from typing import Sequence

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.entities import (
    MusicPreset,
    Project,
    SubtitlePreset,
    User,
    VisualPreset,
    VoicePreset,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def seed() -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        if not admin:
            admin = User(
                email="admin@example.com",
                full_name="Reels Admin",
                password_hash=hash_password("ChangeMe123!"),
                is_admin=True,
            )
            session.add(admin)
            session.flush()

        workspace = session.scalar(select(Workspace).where(Workspace.slug == "north-star-studio"))
        if not workspace:
            workspace = Workspace(
                name="North Star Studio",
                slug="north-star-studio",
                plan_name="Pro Studio",
                seats=5,
                credits_remaining=1000,
                credits_total=1000,
                monthly_budget_cents=500000,
            )
            session.add(workspace)
            session.flush()

        membership = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == admin.id,
            )
        )
        if not membership:
            session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=admin.id,
                    role=WorkspaceRole.admin,
                    is_default=True,
                )
            )

        project = session.scalar(
            select(Project).where(Project.workspace_id == workspace.id, Project.title == "Aurora Serum Launch")
        )
        if not project:
            session.add(
                Project(
                    workspace_id=workspace.id,
                    owner_user_id=admin.id,
                    title="Aurora Serum Launch",
                    client="North Star Studio",
                    aspect_ratio="9:16",
                    duration_target_sec=90,
                )
            )

        _seed_presets(session, workspace.id, admin.id)

        session.commit()
        print("Seed complete. Admin login: admin@example.com / ChangeMe123!")
    finally:
        session.close()


SEED_VISUAL_PRESETS = [
    {
        "name": "Warm Cinematic",
        "description": "Golden hour tones with filmic grain and directional light for lifestyle and beauty content",
        "prompt_prefix": "Warm golden-hour cinematic framing with natural light.",
        "style_descriptor": "Amber highlights, lifted shadows, 35mm grain overlay",
        "negative_prompt": "Avoid harsh lighting, flat colors, overly digital look.",
        "camera_defaults": "Shallow depth-of-field, slow dolly, warm directional key light",
        "color_palette": "Amber, warm ivory, soft peach, burnished gold",
        "reference_notes": "Optimized for lifestyle, beauty, and wellness reels.",
    },
    {
        "name": "Editorial Clean",
        "description": "Cool daylight palette with negative space — perfect for premium product and skincare reels",
        "prompt_prefix": "Premium editorial product photography with clean space.",
        "style_descriptor": "Frosted cobalt / ivory, matte surfaces, diffused high-key lighting",
        "negative_prompt": "Avoid clutter, warm tones, heavy shadows.",
        "camera_defaults": "Static or slow zoom, diffused top lighting, high-key exposure",
        "color_palette": "Frosted cobalt, ivory, cool grey, silver",
        "reference_notes": "Ideal for skincare, premium product, and fashion editorial.",
    },
    {
        "name": "Neon Streetwear",
        "description": "High-contrast nighttime aesthetic with saturated neon accents for fashion and music content",
        "prompt_prefix": "Urban nighttime neon-lit street photography.",
        "style_descriptor": "Deep blacks, magenta / cyan neon spill, anamorphic flares",
        "negative_prompt": "Avoid daylight, muted colors, soft focus.",
        "camera_defaults": "Handheld, tight framing, anamorphic lens flares, hard cuts",
        "color_palette": "Deep black, magenta, cyan, electric blue",
        "reference_notes": "Best for streetwear, music drops, and nightlife content.",
    },
]

SEED_VOICE_PRESETS = [
    {
        "name": "Confident Narrator",
        "description": "Clear, authoritative delivery at a measured pace — ideal for explainers and product launches",
        "provider_voice": "en-US-Guy",
        "tone_descriptor": "Authoritative, clear, measured, professional",
        "language_code": "en-US",
        "pace_multiplier": 1.0,
    },
    {
        "name": "Warm Storyteller",
        "description": "Friendly, conversational female voice with natural pacing for lifestyle and wellness content",
        "provider_voice": "en-US-Jenny",
        "tone_descriptor": "Friendly, conversational, warm, approachable",
        "language_code": "en-US",
        "pace_multiplier": 1.0,
    },
    {
        "name": "Ava Editorial",
        "description": "Polished, calm, and measured — the premium voice for luxury brand campaigns",
        "provider_voice": "en-US-Ava",
        "tone_descriptor": "Polished, calm, elegant, luxurious",
        "language_code": "en-US",
        "pace_multiplier": 0.95,
    },
    {
        "name": "Energetic Host",
        "description": "Upbeat, fast-paced male voice that drives urgency — great for promos, drops, and hype reels",
        "provider_voice": "en-US-Davis",
        "tone_descriptor": "Energetic, upbeat, urgent, dynamic",
        "language_code": "en-US",
        "pace_multiplier": 1.15,
    },
]

SEED_MUSIC_PRESETS = [
    {
        "name": "Lo-Fi Chill",
        "description": "Mellow lo-fi hip-hop bed with vinyl crackle — works under narration without competing",
        "track_name": "Lo-Fi Chill Bed",
        "genre": "lo-fi",
        "ducking_db": -18,
        "fade_in_sec": 2.0,
        "fade_out_sec": 3.0,
        "reference_notes": "Best for lifestyle, wellness, and ambient background.",
    },
    {
        "name": "Upbeat Electronic",
        "description": "Bright, driving synth track that energizes social reels and product reveal sequences",
        "track_name": "Upbeat Synth Drive",
        "genre": "electronic",
        "ducking_db": -14,
        "fade_in_sec": 0.5,
        "fade_out_sec": 2.0,
        "reference_notes": "Great for product reveals, social reels, and promos.",
    },
    {
        "name": "Corporate Ambient",
        "description": "Clean, minimal ambient pad for B2B, SaaS demos, and professional explainer videos",
        "track_name": "Ambient Corporate Pad",
        "genre": "ambient",
        "ducking_db": -20,
        "fade_in_sec": 3.0,
        "fade_out_sec": 4.0,
        "reference_notes": "Suited for B2B, SaaS, and professional explainers.",
    },
]

SEED_SUBTITLE_PRESETS = [
    {
        "name": "Karaoke Bold",
        "description": "Large, word-highlighted captions that pop on screen — the standard for TikTok and Reels engagement",
        "subtitle_style": "karaoke_bold",
        "font_family": "Montserrat",
        "position": "center-bottom",
        "color_scheme": "white_black_stroke_accent_highlight",
        "highlight_mode": "word",
        "reference_notes": "Standard for TikTok and Instagram Reels engagement.",
    },
    {
        "name": "Minimal Lower Third",
        "description": "Understated sans-serif captions pinned to the lower third — clean and professional",
        "subtitle_style": "lower_third",
        "font_family": "Inter",
        "position": "lower-third",
        "color_scheme": "white_on_dark_bar",
        "highlight_mode": "sentence",
        "reference_notes": "Professional look for corporate and editorial content.",
    },
]


def _seed_presets(session, workspace_id, user_id):
    existing_visual = {
        p.name
        for p in session.scalars(select(VisualPreset).where(VisualPreset.workspace_id == workspace_id)).all()
    }
    for data in SEED_VISUAL_PRESETS:
        if data["name"] not in existing_visual:
            session.add(VisualPreset(workspace_id=workspace_id, created_by_user_id=user_id, **data))

    existing_voice = {
        p.name
        for p in session.scalars(select(VoicePreset).where(VoicePreset.workspace_id == workspace_id)).all()
    }
    for data in SEED_VOICE_PRESETS:
        if data["name"] not in existing_voice:
            session.add(VoicePreset(workspace_id=workspace_id, created_by_user_id=user_id, **data))

    existing_music = {
        p.name
        for p in session.scalars(select(MusicPreset).where(MusicPreset.workspace_id == workspace_id)).all()
    }
    for data in SEED_MUSIC_PRESETS:
        if data["name"] not in existing_music:
            session.add(MusicPreset(workspace_id=workspace_id, created_by_user_id=user_id, **data))

    existing_subtitle = {
        p.name
        for p in session.scalars(select(SubtitlePreset).where(SubtitlePreset.workspace_id == workspace_id)).all()
    }
    for data in SEED_SUBTITLE_PRESETS:
        if data["name"] not in existing_subtitle:
            session.add(SubtitlePreset(workspace_id=workspace_id, created_by_user_id=user_id, **data))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reels backend CLI")
    parser.add_argument("command", choices=["seed"])
    args = parser.parse_args(argv)
    if args.command == "seed":
        seed()
