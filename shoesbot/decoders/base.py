from __future__ import annotations
from typing import List
from PIL import Image
from shoesbot.models import Barcode

class Decoder:
    name: str = "decoder"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        raise NotImplementedError
