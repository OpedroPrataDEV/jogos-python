"""
Importa o PPlay tanto na instalação oficial da UFF ("PPlay", com P maiúsculo,
típica do Windows/PyCharm) quanto na versão do pip ("pplay", minúsculo).
"""
try:
    from PPlay.window import Window
    from PPlay.sprite import Sprite
except ImportError:  # pragma: no cover
    from pplay.window import Window
    from pplay.sprite import Sprite

__all__ = ["Window", "Sprite"]
