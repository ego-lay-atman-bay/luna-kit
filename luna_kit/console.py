from rich.console import Console
from rich.progress import Progress, ProgressType, ProgressColumn
from typing import Union, Optional
from collections.abc import Iterable, Sequence

console = Console(quiet = False)


def track(
    sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
    total: Optional[float] = None,
    description: str = 'Working...',
    transient: bool = False,
    columns: list[str | ProgressColumn] | None = None,
):
    progress = Progress(
        *(columns or ()),
        console = console,
        transient = transient,
    )

    with progress:
        yield from progress.track(
            sequence = sequence,
            description = description,
        )
