from __future__ import annotations
from typing import List
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
        self.tpl = self.env.get_template("barcode_card.html.j2")

    def render_barcodes_html(self, barcodes: List[Barcode]) -> str:
        return self.tpl.render(barcodes=barcodes)
