from html import escape as _esc


def esc(x) -> str:
    return _esc(str(x), quote=True)
