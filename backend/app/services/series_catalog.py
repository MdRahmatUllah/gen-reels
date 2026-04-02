from __future__ import annotations

from copy import deepcopy


SERIES_CATALOG: dict[str, list[dict[str, object]]] = {
    "content_presets": [
        {
            "key": "scary_stories",
            "label": "Scary stories",
            "description": "Scary stories that give you goosebumps",
        },
        {
            "key": "historical_figures",
            "label": "Historical Figures",
            "description": "Life story in one minute videos about the most important historical figures.",
        },
        {
            "key": "greek_mythology",
            "label": "Greek Mythology",
            "description": "Shocking and dramatic stories from Greek mythology.",
        },
        {
            "key": "important_events",
            "label": "Important Events",
            "description": "Viral videos about history spanning from ancient times to the modern day.",
        },
        {
            "key": "true_crime",
            "label": "True Crime",
            "description": "Viral videos about true crime stories.",
        },
        {
            "key": "stoic_motivation",
            "label": "Stoic Motivation",
            "description": "Viral videos about stoic philosophy and life lessons.",
        },
        {
            "key": "good_morals",
            "label": "Good morals",
            "description": "Viral videos that teach people good morals and life lessons.",
        },
    ],
    "languages": [
        {
            "key": "en",
            "label": "English",
            "description": "English narration and script generation.",
        }
    ],
    "voices": [
        {
            "key": "adam",
            "label": "Adam",
            "description": "The well known voice of tiktok and instagram.",
            "gender": "male",
        },
        {
            "key": "john",
            "label": "John",
            "description": "The perfect storyteller, very realistic and natural.",
            "gender": "male",
        },
        {
            "key": "confident_narrator",
            "label": "Confident Narrator",
            "description": "Clear, authoritative delivery at a measured pace.",
            "gender": "male",
        },
        {
            "key": "warm_storyteller",
            "label": "Warm Storyteller",
            "description": "Friendly, conversational delivery with natural pacing.",
            "gender": "female",
        },
        {
            "key": "ava_editorial",
            "label": "Ava Editorial",
            "description": "Polished, calm, and measured for premium storytelling.",
            "gender": "female",
        },
        {
            "key": "energetic_host",
            "label": "Energetic Host",
            "description": "Upbeat, fast-paced delivery that drives urgency.",
            "gender": "male",
        },
    ],
    "music": [
        {
            "key": "happy_rhythm",
            "label": "Happy rhythm",
            "description": "Upbeat and energetic, perfect for positive content",
        },
        {
            "key": "quiet_before_storm",
            "label": "Quiet before storm",
            "description": "Building tension and anticipation for dramatic reveals",
        },
        {
            "key": "brilliant_symphony",
            "label": "Brilliant symphony",
            "description": "Orchestral and majestic for epic storytelling",
        },
        {
            "key": "breathing_shadows",
            "label": "Breathing shadows",
            "description": "Mysterious and eerie ambiance for suspenseful videos",
        },
        {
            "key": "eight_bit_slowed",
            "label": "8-bit slowed",
            "description": "Eerie chiptune with a haunting retro feel",
        },
        {
            "key": "deep_bass",
            "label": "Deep bass",
            "description": "Dark interstellar atmosphere with deep low-end",
        },
    ],
    "art_styles": [
        {"key": "comic", "label": "Comic", "description": "Comic-inspired visual treatment."},
        {"key": "creepy_comic", "label": "Creepy Comic", "description": "Dark comic-book framing."},
        {"key": "modern_cartoon", "label": "Modern Cartoon", "description": "Clean contemporary cartoon look."},
        {"key": "disney", "label": "Disney", "description": "Whimsical family-animation inspired style."},
        {"key": "mythology", "label": "Mythology", "description": "Epic myth-inspired visual language."},
        {"key": "pixel_art", "label": "Pixel Art", "description": "Retro pixel-art rendering."},
        {"key": "ghibli", "label": "Ghibli", "description": "Painterly storybook animation aesthetic."},
        {"key": "anime", "label": "Anime", "description": "Anime-inspired character and scene styling."},
        {"key": "painting", "label": "Painting", "description": "Painterly fine-art treatment."},
        {"key": "dark_fantasy", "label": "Dark Fantasy", "description": "Moody fantasy illustration style."},
        {"key": "lego", "label": "Lego", "description": "Toy-brick inspired visuals."},
        {"key": "polaroid", "label": "Polaroid", "description": "Instant-film nostalgic framing."},
        {"key": "realism", "label": "Realism", "description": "Photorealistic storytelling style."},
        {"key": "fantastic", "label": "Fantastic", "description": "Bold imaginative fantasy visuals."},
    ],
    "caption_styles": [
        {"key": "bold_stroke", "label": "Bold Stroke", "description": "Bold outlined captions."},
        {"key": "red_highlight", "label": "Red Highlight", "description": "Key words accented in red."},
        {"key": "sleek", "label": "Sleek", "description": "Minimal modern caption style."},
        {"key": "karaoke", "label": "Karaoke", "description": "Word-by-word karaoke emphasis."},
        {"key": "majestic", "label": "Majestic", "description": "Dramatic cinematic caption look."},
        {"key": "beast", "label": "Beast", "description": "Punchy high-energy caption treatment."},
        {"key": "elegant", "label": "Elegant", "description": "Refined minimal caption styling."},
        {"key": "pixel", "label": "Pixel", "description": "Retro pixel-style captions."},
        {"key": "clarity", "label": "Clarity", "description": "Clean high-legibility captions."},
    ],
    "effects": [
        {
            "key": "shake_effect",
            "label": "Shake effect",
            "description": "Subjects pop out with eerie motion — great for horror, thriller, and suspenseful stories.",
            "badge": "new",
        },
        {
            "key": "film_grain",
            "label": "Film grain",
            "description": "Add an old film look with scanlines, dust particles, noise, and a subtle vignette.",
            "badge": "new",
        },
        {
            "key": "animated_hook",
            "label": "Animated hook",
            "description": "Generate a 5-second motion video for the first scene to hook viewers instantly.",
            "badge": "premium",
        },
    ],
}


def get_series_catalog() -> dict[str, list[dict[str, object]]]:
    return deepcopy(SERIES_CATALOG)


def get_catalog_option(section: str, key: str) -> dict[str, object] | None:
    for item in SERIES_CATALOG.get(section, []):
        if item["key"] == key:
            return deepcopy(item)
    return None


def get_catalog_keys(section: str) -> set[str]:
    return {str(item["key"]) for item in SERIES_CATALOG.get(section, [])}
