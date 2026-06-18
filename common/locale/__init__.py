import gettext
import os

localedir = os.path.join(os.path.dirname(__file__), "..", "..", "locale")

t = gettext.translation(
    "messages",
    localedir=localedir,
    fallback=True,
)

_ = t.gettext
