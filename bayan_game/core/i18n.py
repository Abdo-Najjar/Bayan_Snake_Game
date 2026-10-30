"""Translations loaded from assets/lang/<code>.json.

Each language file is a nested JSON object. Keys are looked up with dots,
e.g. tr("menu.play"). Values may contain {placeholders} filled from kwargs.
Every file has a "_meta" block: {"name": "...", "rtl": true/false}.
Drop a new <code>.json into the folder and it shows up in Settings.
"""
import json
import os

try:
    import arabic_reshaper
    try:
        from bidi import get_display
    except ImportError:
        from bidi.algorithm import get_display
    HAS_SHAPING = True
except ImportError:
    HAS_SHAPING = False


def _flatten(obj, prefix=""):
    out = {}
    for key, value in obj.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, full + "."))
        else:
            out[full] = str(value)
    return out


def shape(text):
    """Join Arabic letters and order right-to-left text for display."""
    if not HAS_SHAPING:
        return text
    return get_display(arabic_reshaper.reshape(text))


class I18n:
    def __init__(self, lang_dir, code, fallback="en"):
        self.lang_dir = lang_dir
        self.languages = self._discover()
        self.fallback = self._load(fallback)
        self.code = None
        self.strings = {}
        self.rtl = False
        self._cache = {}
        self.set_language(code)

    def _discover(self):
        langs = {}
        if os.path.isdir(self.lang_dir):
            for name in sorted(os.listdir(self.lang_dir)):
                if name.endswith(".json"):
                    code = name[:-5]
                    meta = self._load(code).get("_meta.name", code)
                    langs[code] = meta
        return langs

    def _load(self, code):
        path = os.path.join(self.lang_dir, f"{code}.json")
        try:
            with open(path, encoding="utf-8") as f:
                return _flatten(json.load(f))
        except (OSError, ValueError):
            return {}

    def set_language(self, code):
        if code not in self.languages and self.languages:
            code = next(iter(self.languages))
        self.code = code
        self.strings = self._load(code)
        self.rtl = self.strings.get("_meta.rtl", "False").lower() == "true"
        self._cache.clear()

    def next_language(self, step=1):
        codes = list(self.languages)
        if not codes:
            return self.code
        i = codes.index(self.code) if self.code in codes else 0
        return codes[(i + step) % len(codes)]

    def language_name(self, code=None):
        """Unshaped name, meant to be passed as a value into tr(...)."""
        return self.languages.get(code or self.code, code or "")

    def raw(self, key, **kwargs):
        """Translated text before shaping. Use it for values placed inside other strings."""
        template = self.strings.get(key) or self.fallback.get(key) or key
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template

    def __call__(self, key, **kwargs):
        cache_key = (key, tuple(sorted(kwargs.items())))
        if cache_key in self._cache:
            return self._cache[cache_key]
        text = self.raw(key, **kwargs)
        if self.rtl or (HAS_SHAPING and any(0x600 <= ord(ch) <= 0x6FF for ch in text)):
            text = shape(text)
        if len(self._cache) > 500:
            self._cache.clear()
        self._cache[cache_key] = text
        return text

    def has(self, key):
        return key in self.strings or key in self.fallback
