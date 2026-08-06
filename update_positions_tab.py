from pathlib import Path

APP_FILE = Path("app.py")
REPLACEMENT_FILE = Path("positions_tab_replacement.py")
START_MARKER = "with tab_positions:"
END_MARKER = "with tab_rebalance:"


def main() -> None:
    original = APP_FILE.read_text(encoding="utf-8")
    replacement = REPLACEMENT_FILE.read_text(encoding="utf-8")

    start = original.find(START_MARKER)
    end = original.find(END_MARKER)

    if start == -1:
        raise RuntimeError("Kunne ikke finde starten på Positioner-fanen.")
    if end == -1 or end <= start:
        raise RuntimeError("Kunne ikke finde starten på Rebalancering-fanen.")

    updated = original[:start] + replacement + original[end:]
    compile(updated, "app.py", "exec")
    APP_FILE.write_text(updated, encoding="utf-8")
    print("Positioner-fanen er opdateret.")


if __name__ == "__main__":
    main()
