#!/usr/bin/env python3
"""
Synthetic benchmark for process_photo_batch.

Usage examples:
    python tools/benchmark_bot.py --generate 6 --iterations 3
    python tools/benchmark_bot.py --images "samples/*.jpg" --output bench.json

By default BENCHMARK_MODE=1, so no network traffic (Telegram/Django) occurs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import tempfile
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import List

from PIL import Image, ImageDraw

os.environ.setdefault("BENCHMARK_MODE", "1")

from shoesbot.photo_buffer import PhotoItem  # noqa: E402
from shoesbot.telegram_bot import process_photo_batch  # noqa: E402


class DummyMessage:
    def __init__(self, mid: int):
        self.message_id = mid


class DummyBot:
    def __init__(self, photo_store: dict[str, bytes]):
        self._photo_store = photo_store
        self._mid = 10_000

    async def send_message(self, chat_id: int, text: str, **kwargs):
        self._mid += 1
        return DummyMessage(self._mid)

    async def send_media_group(self, chat_id: int, media_group: List, **kwargs):
        messages = []
        for _ in media_group:
            self._mid += 1
            messages.append(DummyMessage(self._mid))
        return messages

    async def delete_message(self, chat_id: int, message_id: int):
        return True

    async def get_file(self, file_id: str):
        data = self._photo_store.get(file_id)

        class _File:
            def __init__(self, payload: bytes):
                self._payload = payload

            async def download_to_memory(self, out):
                out.write(self._payload)

        return _File(data or b"")


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark process_photo_batch")
    parser.add_argument("--images", nargs="*", help="Image glob(s) to use for benchmark")
    parser.add_argument("--generate", type=int, default=0, help="Generate N synthetic images")
    parser.add_argument("--image-size", default="640x640", help="Generated image size, e.g. 512x512")
    parser.add_argument("--iterations", type=int, default=3, help="Benchmark iterations")
    parser.add_argument("--chat-id", type=int, default=-999999, help="Synthetic chat id")
    parser.add_argument("--output", help="Optional JSON file for results")
    parser.add_argument("--label", help="Optional label for this run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for synthetic data")
    return parser.parse_args()


def load_images(args) -> tuple[list[dict], list[Path]]:
    photo_entries = []
    paths: list[Path] = []

    if args.images:
        for pattern in args.images:
            expanded = list(Path().glob(pattern))
            paths.extend(sorted(p.resolve() for p in expanded))

    temp_dir = None
    if args.generate:
        width, height = (int(x) for x in args.image_size.lower().split("x"))
        temp_dir = Path(tempfile.mkdtemp(prefix="shoesbot_bench_"))
        for idx in range(args.generate):
            img = Image.new("RGB", (width, height), color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            draw = ImageDraw.Draw(img)
            draw.text((20, 20), f"GG{1000+idx}", fill=(255, 255, 255))
            path = temp_dir / f"generated_{idx}.jpg"
            img.save(path, "JPEG", quality=90)
            paths.append(path)

    if not paths:
        raise SystemExit("No images provided. Use --images or --generate.")

    base_message_id = 2000
    for idx, path in enumerate(paths):
        data = path.read_bytes()
        photo_entries.append({
            "file_id": f"bench:{idx}",
            "message_id": base_message_id + idx,
            "bytes": data,
        })

    return photo_entries, paths


def build_photo_item(entry):
    raw = entry["bytes"]
    file_id = entry["file_id"]
    message_id = entry["message_id"]
    annotations = getattr(PhotoItem, "__annotations__", {})
    if "file_bytes" in annotations:
        return PhotoItem(file_id=file_id, message_id=message_id, file_bytes=raw)
    fields = getattr(PhotoItem, "_fields", [])
    if "file_obj" in fields:
        class _MockFile:
            def __init__(self, payload):
                self._payload = payload

            async def download_to_memory(self, out):
                out.write(self._payload)
        return PhotoItem(file_id, _MockFile(raw), message_id)
    raise RuntimeError("Unsupported PhotoItem signature")


async def run_iteration(photo_entries, chat_id):
    photo_store = {entry["file_id"]: entry["bytes"] for entry in photo_entries}
    bot = DummyBot(photo_store)
    context = SimpleNamespace(bot=bot)
    photo_items = [
        build_photo_item(entry)
        for entry in photo_entries
    ]
    start = perf_counter()
    result = await process_photo_batch(chat_id, photo_items, context, status_msg=None)
    duration = perf_counter() - start
    result = result or {}
    result.setdefault("duration", duration)
    return result


def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    photo_entries, paths = load_images(args)
    chat_id = args.chat_id

    results = []
    for i in range(args.iterations):
        iteration_result = asyncio.run(run_iteration(photo_entries, chat_id))
        results.append(iteration_result)
        print(f"[run {i+1}/{args.iterations}] duration={iteration_result.get('duration', 0):.3f}s "
              f"openai={iteration_result.get('openai_used')}")

    durations = [r.get("duration", 0.0) for r in results]
    summary = {
        "label": args.label or "current",
        "iterations": args.iterations,
        "avg_seconds": statistics.mean(durations),
        "stdev_seconds": statistics.pstdev(durations) if len(durations) > 1 else 0.0,
        "min_seconds": min(durations),
        "max_seconds": max(durations),
        "photos": len(photo_entries),
        "images_used": [str(p) for p in paths],
        "openai_runs": sum(1 for r in results if r.get("openai_used")),
        "results": results,
    }

    print("\nSummary:")
    print(json.dumps(summary, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()

