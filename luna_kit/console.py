RICH_LOADED = False
console = None

try:
    from rich.console import Console
    console = Console(quiet = True)
except ImportError:
    pass
