from dataclasses import dataclass

@dataclass(frozen=True)
class Barcode:
    symbology: str
    data: str
    source: str
