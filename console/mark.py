"""The Ledger mark. Its shape lives here only: the sign-in mark and the wordmark both read
it, so a new logo is a change to these two values (docs/design.md, "The mark")."""

from urllib.parse import quote

MARK_VIEWBOX = "0 0 100 140"
MARK_PATH = "M0 0H100V140L50 103.6L0 140Z"


def _mark_svg(fill: str = "#000") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{MARK_VIEWBOX}">'
        f'<path fill="{fill}" d="{MARK_PATH}"/></svg>'
    )


def mark_icon_url() -> str:
    """The mark as the browser tab icon: white on the dark tab strip."""
    return "data:image/svg+xml," + quote(_mark_svg("#F5F5F7"))


def mark_mask_url() -> str:
    """The mark as a CSS url() for mask-image (the wordmark)."""
    svg = _mark_svg()
    return f'url("data:image/svg+xml,{quote(svg)}")'
