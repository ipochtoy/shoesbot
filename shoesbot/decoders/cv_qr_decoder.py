from typing import List
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

class OpenCvQrDecoder(Decoder):
    name = "opencv-qr"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        if not HAS_CV2:
            return []
        arr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        qr = cv2.QRCodeDetector()
        data, points, _ = qr.detectAndDecode(arr)
        if data:
            return [Barcode(symbology="QRCODE", data=str(data), source=self.name)]
        return []
