from __future__ import annotations
from typing import List, Sequence, Tuple, Dict, Any
from time import perf_counter
import asyncio
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder

class DecoderPipeline:
    def __init__(self, decoders: Sequence[Decoder]):
        self.decoders = list(decoders)
        # Quick decoders that are fast (ZBar, OpenCV)
        self.quick_decoders = [d for d in decoders if d.name in ("zbar", "opencv-qr")]
        # Slow decoders that can be skipped (Vision, GG)
        self.slow_decoders = [d for d in decoders if d.name in ("vision-ocr", "gg-label")]

    def run(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        results: List[Barcode] = []
        seen: set[Tuple[str, str]] = set()
        for d in self.decoders:
            try:
                out = d.decode(image, image_bytes)
            except Exception:
                out = []
            for b in out:
                key = (b.symbology, b.data)
                if key in seen:
                    continue
                seen.add(key)
                results.append(b)
        return results

    def run_debug(self, image: Image.Image, image_bytes: bytes) -> tuple[List[Barcode], list[Dict[str, Any]]]:
        timeline: list[Dict[str, Any]] = []
        results: List[Barcode] = []
        seen: set[Tuple[str, str]] = set()
        for d in self.decoders:
            t0 = perf_counter()
            count = 0
            error = None
            try:
                out = d.decode(image, image_bytes)
                for b in out:
                    key = (b.symbology, b.data)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(b)
                    count += 1
            except Exception as e:
                error = repr(e)
            dt = int((perf_counter() - t0) * 1000)
            timeline.append({
                'decoder': getattr(d, 'name', d.__class__.__name__),
                'count': count,
                'ms': dt,
                'error': error,
            })
        return results, timeline
    
    async def run_smart_parallel_debug(self, image: Image.Image, image_bytes: bytes) -> tuple[List[Barcode], list[Dict[str, Any]]]:
        """Run quick decoders first, skip slow ones if quick decoders found barcodes."""
        # Run quick decoders first
        async def decode_one(decoder):
            t0 = perf_counter()
            try:
                out = await asyncio.to_thread(decoder.decode, image, image_bytes)
                error = None
            except Exception as e:
                out = []
                error = repr(e)
            elapsed = perf_counter() - t0
            return out, error, elapsed
        
        # Run quick decoders in parallel
        quick_tasks = [decode_one(d) for d in self.quick_decoders]
        quick_results = await asyncio.gather(*quick_tasks)
        
        # Check if quick decoders found anything (excluding Q-codes which are GG labels)
        found_barcodes = False
        all_results: List[Barcode] = []
        seen: set[Tuple[str, str]] = set()
        
        for out, _, _ in quick_results:
            for b in out:
                key = (b.symbology, b.data)
                if key not in seen:
                    seen.add(key)
                    all_results.append(b)
                    # Check if it's a real barcode (not a Q code)
                    if not (b.symbology == "CODE39" and b.data.startswith("Q")):
                        found_barcodes = True
        
        timeline: list[Dict[str, Any]] = []
        decoder_idx = 0
        
        # Add quick decoder results to timeline
        for idx, decoder in enumerate(self.quick_decoders):
            out, error, elapsed = quick_results[idx]
            count = 0
            for b in out:
                if (b.symbology, b.data) in seen:
                    count += 1
            timeline.append({
                'decoder': getattr(decoder, 'name', decoder.__class__.__name__),
                'count': count,
                'ms': int(elapsed * 1000),
                'error': error,
            })
            decoder_idx += 1
        
        # Skip slow decoders if we found barcodes
        if found_barcodes:
            for decoder in self.slow_decoders:
                timeline.append({
                    'decoder': getattr(decoder, 'name', decoder.__class__.__name__),
                    'count': 0,
                    'ms': 0,
                    'error': None,
                })
        else:
            # Run slow decoders in parallel
            slow_tasks = [decode_one(d) for d in self.slow_decoders]
            slow_results = await asyncio.gather(*slow_tasks)
            
            for idx, (out, error, elapsed) in enumerate(slow_results):
                count = 0
                for b in out:
                    key = (b.symbology, b.data)
                    if key not in seen:
                        seen.add(key)
                        all_results.append(b)
                        count += 1
                timeline.append({
                    'decoder': getattr(self.slow_decoders[idx], 'name', '?'),
                    'count': count,
                    'ms': int(elapsed * 1000),
                    'error': error,
                })
        
        return all_results, timeline
    
    async def run_parallel_debug(self, image: Image.Image, image_bytes: bytes) -> tuple[List[Barcode], list[Dict[str, Any]]]:
        """Run decoders in parallel using asyncio.gather()."""
        async def decode_one(decoder):
            t0 = perf_counter()
            try:
                out = await asyncio.to_thread(decoder.decode, image, image_bytes)
                error = None
            except Exception as e:
                out = []
                error = repr(e)
            elapsed = perf_counter() - t0
            return out, error, elapsed
        
        # Run all decoders in parallel
        tasks = [decode_one(d) for d in self.decoders]
        decoder_results = await asyncio.gather(*tasks)
        
        # Deduplicate and build timeline
        results: List[Barcode] = []
        timeline: list[Dict[str, Any]] = []
        seen: set[Tuple[str, str]] = set()
        
        for idx, (out, error, elapsed) in enumerate(decoder_results):
            count = 0
            for b in out:
                key = (b.symbology, b.data)
                if key not in seen:
                    seen.add(key)
                    results.append(b)
                    count += 1
            timeline.append({
                'decoder': getattr(self.decoders[idx], 'name', self.decoders[idx].__class__.__name__),
                'count': count,
                'ms': int(elapsed * 1000),
                'error': error,
            })
        return results, timeline
