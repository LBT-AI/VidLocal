import importlib
import pkgutil

from .base import BaseDownloader


DOWNLOADERS = []


def load_downloaders():
    DOWNLOADERS.clear()
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{module_name}")
        for attr in dir(module):
            obj = getattr(module, attr)
            try:
                if issubclass(obj, BaseDownloader) and obj != BaseDownloader:
                    DOWNLOADERS.append(obj())
            except Exception:
                pass


load_downloaders()


__all__ = ["BaseDownloader", "DOWNLOADERS", "load_downloaders"]
