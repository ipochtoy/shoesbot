from __future__ import annotations
from typing import List
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from shoesbot.models import Barcode

class CardRenderer:
    def __init__(self, templates_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.use_v2 = os.getenv("CARD_TEMPLATE_V2", "1") == "1"
        self._load_template()

    def _load_template(self):
        template_name = "barcode_card_v2.html.j2" if self.use_v2 else "barcode_card.html.j2"
        self.tpl = self.env.get_template(template_name)

    def render_barcodes_html(self, barcodes: List[Barcode], photo_count: int = 1) -> str:
        return self.tpl.render(barcodes=barcodes, photo_count=photo_count)
