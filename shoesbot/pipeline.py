from __future__ import annotations
from typing import List, Sequence, Tuple, Dict, Any
from time import perf_counter
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder

class DecoderPipeline:
    def __init__(self, decoders: Sequence[Decoder]):
        self.decoders = list(decoders)

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
