#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, '/Users/dzianismazol/Projects/shoesbot')
os.environ['GOOGLE_VISION_API_KEY'] = 'AIzaSyCkYrxXAc4K4wkty_CyTrOu0e2ZswadBL4'
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

from shoesbot.decoders.gg_label_decoder import GGLabelDecoder
from shoesbot.decoders.zbar_decoder import ZBarDecoder

test_dir = Path('/Users/dzianismazol/Projects/shoesbot/data/test_images')
gg_decoder = GGLabelDecoder()
zbar = ZBarDecoder()

print("Quick scan of all images:\n")
for img_path in sorted(test_dir.glob('*.jpg')):
    img = Image.open(img_path)
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    
    gg_results = gg_decoder.decode(img, img_bytes)
    zbar_results = zbar.decode(img, img_bytes)
    q_codes = [r for r in zbar_results if r.symbology == 'CODE39' and r.data.startswith('Q')]
    
    if gg_results or q_codes:
        print(f"{img_path.name}:")
        if gg_results:
            print(f"  GG: {', '.join([r.data for r in gg_results])}")
        if q_codes:
            print(f"  Q: {', '.join([r.data for r in q_codes])}")

