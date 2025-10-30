from typing import List
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder

try:
    from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode
    HAS_ZBAR = True
except Exception:
    HAS_ZBAR = False

class ZBarDecoder(Decoder):
    name = "zbar"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        if not HAS_ZBAR:
            return []
        symbols = [
            ZBarSymbol.QRCODE,
            ZBarSymbol.EAN13,
            ZBarSymbol.EAN8,
            ZBarSymbol.UPCA,
            ZBarSymbol.UPCE,
            ZBarSymbol.CODE39,
            ZBarSymbol.CODE93,
            ZBarSymbol.CODE128,
        ]
        results = zbar_decode(image, symbols=symbols)
        out: List[Barcode] = []
        for r in results:
            try:
                data = r.data.decode("utf-8", errors="replace")
            except Exception:
                data = str(r.data)
            out.append(Barcode(symbology=str(r.type), data=data, source=self.name))
        return out
