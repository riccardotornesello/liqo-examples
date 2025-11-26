import sys

import readchar
from readchar import key
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.console import Group
from rich import box

from actors import test_forwarding


# --- DATA CONFIGURATION ---
OPTIONS_POOL = {
    "block_ingress": ["off", "strict", "isolation"],
    "offloaded_isolation": ["off", "peerings", "full"],
}

ROW_MAP = [
    ("CONSUMER", "block_ingress"),
    ("CONSUMER", "offloaded_isolation"),
    ("PROVIDER", "block_ingress"),
    ("PROVIDER", "offloaded_isolation"),
]

PODS_LIST = ["PC", "POC", "POP", "PP", "PXP"]

# --- STATE MANAGEMENT ---
state = {
    "CONSUMER": {
        "block_ingress": "off",
        "offloaded_isolation": "off",
    },
    "PROVIDER": {
        "block_ingress": "off",
        "offloaded_isolation": "off",
    },
}

current_row_index = 0
console = Console()


# --- LOGIC FUNCTIONS ---
def cycle_option(direction):
    """Change the value of the selected row (left/right)."""
    cluster, setting = ROW_MAP[current_row_index]
    current_val = state[cluster][setting]
    options = OPTIONS_POOL[setting]

    idx = options.index(current_val)

    if direction == "NEXT":
        new_idx = (idx + 1) % len(options)
    else:
        new_idx = (idx - 1) % len(options)

    state[cluster][setting] = options[new_idx]


def move_cursor(direction):
    """Move the current row selection up or down."""
    global current_row_index
    if direction == "UP":
        current_row_index = (current_row_index - 1) % len(ROW_MAP)
    elif direction == "DOWN":
        current_row_index = (current_row_index + 1) % len(ROW_MAP)


# --- RENDERING FUNCTIONS ---
def get_config_table():
    """Create the configuration table with the current row highlighted."""
    table = Table(box=box.ROUNDED, expand=True)
    table.add_column("Cluster", style="magenta", width=12)
    table.add_column("Setting", style="cyan", width=20)
    table.add_column("Value (Use ⬅ ➡ to change)", justify="center")

    for i, (cluster, setting) in enumerate(ROW_MAP):
        value = state[cluster][setting]

        # Highlight the current row
        if i == current_row_index:
            # Highlight using reverse colors and arrows
            style_val = "black on yellow"
            display_val = f"◀ {value.upper()} ▶"
            display_cluster = f"[b reverse]{cluster}[/]"
            display_setting = f"[b reverse]{setting}[/]"
        else:
            style_val = "green"
            display_val = value
            display_cluster = (
                cluster if (i % 2 == 0) else ""
            )  # Show cluster name only on the first row of the group
            display_setting = setting

        table.add_row(
            display_cluster, display_setting, Text(display_val, style=style_val)
        )

    return table


def get_ping_table():
    """Generate the ping table (always successful for now)."""
    table = Table(title="[italic]Live Connectivity Check[/italic]", box=box.SIMPLE)

    # Forwarding table calculation
    forward_matrix = {
        p: {
            q: test_forwarding(p, q, state["CONSUMER"], state["PROVIDER"])
            for q in PODS_LIST
        }
        for p in PODS_LIST
    }

    # Columns
    table.add_column("Src \\ Dst", style="dim")
    for p in PODS_LIST:
        table.add_column(p, justify="center")

    # Rows
    for p in PODS_LIST:
        row_vals = [p]
        for q in PODS_LIST:
            if p == q:
                row_vals.append("-")
            elif forward_matrix[p][q] == True:
                row_vals.append("[bold green]OK[/]")
            else:
                row_vals.append("[bold red]KO[/]")
        table.add_row(*row_vals)

    return Panel(table, border_style="dim")


def generate_layout():
    """Assemble the entire interface."""
    header = Text("NETWORK SIMULATOR CLI", justify="center", style="bold white on blue")
    instructions = Text(
        "⬆/⬇: Select | ⬅/➡: Modify | Enter: Confirm | Ctrl+C: Exit",
        justify="center",
        style="dim",
    )

    return Group(
        header,
        Text(""),
        get_config_table(),
        Text(""),
        get_ping_table(),
        Text(""),
        instructions,
    )


# --- MAIN LOOP ---
def main():
    # Hide the terminal cursor
    console.show_cursor(False)

    try:
        # Start Live rendering
        with Live(generate_layout(), refresh_per_second=20, screen=True) as live:
            while True:
                # Capture the pressed key
                k = readchar.readkey()

                if k == key.UP:
                    move_cursor("UP")
                elif k == key.DOWN:
                    move_cursor("DOWN")
                elif k == key.RIGHT:
                    cycle_option("NEXT")
                elif k == key.LEFT:
                    cycle_option("PREV")
                elif k == key.ENTER:
                    # Confirm exit
                    break
                elif k == key.CTRL_C:
                    sys.exit(0)

                # Update layout after input
                live.update(generate_layout())

    except KeyboardInterrupt:
        pass
    finally:
        console.show_cursor(True)
        console.print("[bold green]Configuration saved![/bold green]")
        console.print(state)


if __name__ == "__main__":
    main()
