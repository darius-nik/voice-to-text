import re
from typing import Optional

try:
    from hazm import Normalizer
except Exception:  # pragma: no cover
    Normalizer = None  # type: ignore

try:
    from persiantools import digits
except Exception:  # pragma: no cover
    digits = None  # type: ignore

# Optional Arabic shaping and bidi display
try:
    import arabic_reshaper  # type: ignore
except Exception:  # pragma: no cover
    arabic_reshaper = None  # type: ignore

try:
    from bidi.algorithm import get_display  # type: ignore
except Exception:  # pragma: no cover
    def get_display(x: str) -> str:  # type: ignore
        return x

_PERSIAN_REGEX = re.compile(r"[\u0600-\u06FF]")

_normalizer: Optional["Normalizer"] = None

def _get_normalizer() -> Optional["Normalizer"]:
    global _normalizer
    if _normalizer is None and Normalizer is not None:
        # Hazm normalizer options tuned for readable Persian text
        _normalizer = Normalizer(
            remove_diacritics=True,
            persian_numbers=False,   # we'll control digits separately
            remove_extra_spaces=True,
            lowercase=False
        )
    return _normalizer

def is_persian_text(text: str) -> bool:
    """Heuristically detect if text contains Persian/Arabic script characters."""
    return bool(_PERSIAN_REGEX.search(text or ""))

def normalize_persian(text: str, *, convert_digits_to_persian: bool = True) -> str:
    """Normalize Persian text for readability.

    - Fix Arabic vs Persian letters (ك→ک, ي→ی)
    - Unify whitespace and punctuation spacing
    - Remove tatweel/diacritics
    - Optionally convert digits to Persian
    """
    if not text:
        return text

    # Map Arabic forms to Persian equivalents
    text = (
        text.replace("\u064A", "\u06CC")  # ي -> ی
            .replace("\u0643", "\u06A9")  # ك -> ک
            .replace("\u06C0", "\u0629")  # ۀ -> ة (rare; keep as-is if needed)
    )

    # Hazm normalization (if available)
    norm = _get_normalizer()
    if norm is not None:
        try:
            text = norm.normalize(text)
        except Exception:
            pass

    # Punctuation spacing fixes around ، ؛ ؟ ! .
    text = re.sub(r"\s*([,،؛\!\?\.:])\s*", r"\1 ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Optional digit conversion
    if convert_digits_to_persian and digits is not None:
        try:
            text = digits.en_to_fa(text)
        except Exception:
            pass

    return text

def shape_bidi_display(text: str) -> str:
    """Return a visually-correct RTL display string using Arabic reshaping + bidi.

    This is intended for on-screen display only. Do not use the shaped string for saving/copying
    if you need logical order; use the original normalized text for clipboard/file.
    """
    if not text:
        return text
    # Reshape for proper glyph joining
    if arabic_reshaper is not None:
        try:
            reshaped = arabic_reshaper.reshape(text)
        except Exception:
            reshaped = text
    else:
        reshaped = text
    # Apply bidi algorithm to get correct RTL visual order
    try:
        visual = get_display(reshaped)
    except Exception:
        visual = reshaped
    return visual
