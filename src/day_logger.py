"""Day Logger - Extract MISSING capabilities from logs and build nightly queue."""

import argparse
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from .models.queue import NightlyQueue, QueueItem

MISSING_PATTERN = re.compile(r"\[MISSING:\s*(.+?)\]")


def parse_log(log_path: Path) -> list[tuple[str, str]]:
    """Extract all MISSING capability descriptions from a log file.

    Args:
        log_path: Path to the log file to parse.

    Returns:
        List of (capability, context_line) tuples.
    """
    results: list[tuple[str, str]] = []
    with open(log_path) as f:
        for line in f:
            match = MISSING_PATTERN.search(line)
            if match:
                capability = match.group(1).strip()
                context_line = line.strip()
                results.append((capability, context_line))
    return results


def build_queue(
    capabilities: list[tuple[str, str]], existing: NightlyQueue | None = None
) -> NightlyQueue:
    """Build a deduplicated queue from capabilities, merging with existing queue.

    Deduplication is case-insensitive and strips whitespace.
    Existing items preserve their status; occurrences are incremented.

    Args:
        capabilities: List of (capability, context_line) tuples.
        existing: Optional existing queue to merge with.

    Returns:
        NightlyQueue with deduplicated items.
    """
    # Build lookup from existing items (case-insensitive key)
    existing_lookup: dict[str, QueueItem] = {}
    if existing:
        for item in existing.items:
            key = item.capability.lower().strip()
            existing_lookup[key] = item

    # Track new items by normalized key
    new_items: dict[str, QueueItem] = {}

    for capability, context in capabilities:
        key = capability.lower().strip()

        if key in existing_lookup:
            # Increment occurrences on existing item, preserve status
            existing_lookup[key].occurrences += 1
        elif key in new_items:
            # Increment occurrences on new item we've already seen
            new_items[key].occurrences += 1
        else:
            # Create new item
            new_items[key] = QueueItem(
                id=str(uuid.uuid4()),
                capability=capability.strip(),
                first_seen=datetime.now(),
                occurrences=1,
                context=context,
                status="pending",
            )

    # Combine: existing items first, then new items
    all_items = list(existing_lookup.values()) + list(new_items.values())

    return NightlyQueue(items=all_items, updated_at=datetime.now())


def main() -> None:
    """CLI entry point for day logger."""
    parser = argparse.ArgumentParser(
        description="Extract MISSING capabilities from logs and build nightly queue"
    )
    parser.add_argument("--log", required=True, help="Path to input log file")
    parser.add_argument("--out", required=True, help="Path to output queue JSON file")
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)

    # Parse log
    capabilities = parse_log(log_path)

    # Load existing queue if output file exists
    existing: NightlyQueue | None = None
    if out_path.exists():
        with open(out_path) as f:
            data = json.load(f)
            existing = NightlyQueue.model_validate(data)

    # Build queue
    queue = build_queue(capabilities, existing)

    # Write output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(queue.model_dump(mode="json"), f, indent=2, default=str)

    # Print summary
    new_count = len([i for i in queue.items if i.status == "pending"])
    total_count = len(queue.items)
    print(f"Parsed {len(capabilities)} MISSING tags from {log_path}")
    print(f"Queue now has {total_count} items ({new_count} pending)")


if __name__ == "__main__":
    main()
