from __future__ import annotations
from typing import Iterable, List, Sequence, Tuple
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
