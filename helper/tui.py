"""Terminal UI for the smart pantry, built with Rich (pip install rich).

render() builds one frame from the current state. main.py shows it with rich.live.Live,
which redraws it in place; log lines printed meanwhile appear above it."""
import time

from rich.console import Group
from rich.table import Table
from rich.text import Text

MACRO_COLUMNS = (("calories", "kcal", "bold yellow"),
                 ("fat", "Fat (g)", "magenta"),
                 ("protein", "Protein (g)", "cyan"),
                 ("carbs", "Carbs (g)", "green"))

STATUS_STYLE = {"ready": "bold green", "waiting for scale": "bold yellow"}


def _header(status, weight):
    weight_text = f"{weight[0]:.0f} {weight[1]}" if weight else "—"
    return Text.assemble(
        (" SMART PANTRY ", "bold white on blue"), "  ",
        ("status: ", "dim"), (status, STATUS_STYLE.get(status, "bold red")), "  ",
        ("scale: ", "dim"), (weight_text, "bold white"),
    )


def _inventory_table(ledger):
    totals = ledger.totals()
    servings = ledger.servings()
    item_macros = ledger.item_macros()

    table = Table(title="Inventory", title_style="bold", expand=True, header_style="bold")
    table.add_column("Item", style="bold white")
    table.add_column("Grams", justify="right")
    table.add_column("Servings", justify="right")
    for _, title, style in MACRO_COLUMNS:
        table.add_column(title, justify="right", style=style)

    shown = [(item, grams) for item, grams in totals.items() if grams > 0]
    if not shown:
        table.add_row(Text("empty", style="dim italic"), "", "", *[""] * len(MACRO_COLUMNS))
    for item, grams in shown:
        macros = item_macros.get(item)
        serving_text = f"{servings[item]:.1f}" if item in servings else Text("—", style="dim")
        macro_cells = ([f"{macros[key]:.1f}" for key, _, _ in MACRO_COLUMNS] if macros
                       else [Text("?", style="dim")] * len(MACRO_COLUMNS))
        table.add_row(item, f"{grams:.0f}", serving_text, *macro_cells)

    total = ledger.macros()
    table.add_section()
    table.add_row(Text("TOTAL", style="bold"), "", "",
                  *[Text(f"{total[key]:.1f}", style=f"bold {style}") for key, _, style in MACRO_COLUMNS])
    return table


def _entries_table(ledger):
    table = Table(title="Recent changes", title_style="bold", expand=True, header_style="bold")
    table.add_column("Time", style="dim")
    table.add_column("Item", style="bold white")
    table.add_column("Change", justify="right")
    entries = ledger.entries()
    if not entries:
        table.add_row(Text("none yet", style="dim italic"), "", "")
    for entry in reversed(entries):                       # newest first
        style = "bold green" if entry.delta > 0 else "bold red"
        table.add_row(time.strftime("%H:%M:%S", time.localtime(entry.timestamp)),
                      entry.item, Text(f"{entry.delta:+.0f} g", style=style))
    return table


def render(ledger, status, weight):
    """One frame: header, inventory with macros and servings, and recent changes.
    weight: the scale's current (value, unit, status), or None."""
    return Group(_header(status, weight), _inventory_table(ledger), _entries_table(ledger))