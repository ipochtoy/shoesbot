#!/usr/bin/env python3
"""
Evaluation harness for barcode/GG label decoders.
Tests decoder pipeline on sample images and reports hit rates and timings.
"""
import os
import sys
import json
import csv
from pathlib import Path
from time import perf_counter
from PIL import Image
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

from shoesbot.pipeline import DecoderPipeline
from shoesbot.decoders.zbar_decoder import ZBarDecoder
from shoesbot.decoders.cv_qr_decoder import OpenCvQrDecoder
from shoesbot.decoders.vision_decoder import VisionDecoder
from shoesbot.decoders.gg_label_decoder import GGLabelDecoder

# Optional improved decoders
try:
    from shoesbot.decoders.gg_label_decoder_improved import ImprovedGGLabelDecoder
    HAS_IMPROVED_GG = True
except ImportError:
    HAS_IMPROVED_GG = False

try:
    from shoesbot.decoders.zbar_enhanced import EnhancedZBarDecoder
    HAS_ENHANCED_ZBAR = True
except ImportError:
    HAS_ENHANCED_ZBAR = False


def evaluate_image(pipeline: DecoderPipeline, image_path: str) -> Dict[str, Any]:
    """Evaluate a single image with the pipeline."""
    try:
        img = Image.open(image_path).convert("RGB")
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        
        t0 = perf_counter()
        # Use simple run_debug (not parallel/async) for accurate evaluation
        results, timeline = pipeline.run_debug(img, img_bytes)
        total_time = perf_counter() - t0
        
        # Extract GG/Q labels
        gg_labels = [r for r in results if r.symbology in ('GG_LABEL', 'GG')]
        q_codes = [r for r in results if r.symbology == 'CODE39' and r.data.startswith('Q')]
        regular_barcodes = [r for r in results if r not in gg_labels and r not in q_codes]
        
        return {
            'image': os.path.basename(image_path),
            'total_time_ms': int(total_time * 1000),
            'total_results': len(results),
            'gg_labels': [r.data for r in gg_labels],
            'q_codes': [r.data for r in q_codes],
            'regular_barcodes': [r.data for r in regular_barcodes],
            'timeline': timeline,
            'success': True
        }
    except Exception as e:
        return {
            'image': os.path.basename(image_path),
            'error': str(e),
            'success': False
        }


def run_evaluation(test_dir: str, output_file: str = None):
    """Run evaluation on all images in test directory."""
    test_path = Path(test_dir)
    if not test_path.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    # Find all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(test_path.glob(ext))
        image_files.extend(test_path.glob(ext.upper()))
    
    if not image_files:
        print(f"❌ No images found in {test_dir}")
        return
    
    print(f"📸 Found {len(image_files)} images")
    print(f"🔬 Initializing pipeline...")
    
    # Build decoder list based on environment flags (same as production bot)
    USE_IMPROVED_GG = os.getenv("USE_IMPROVED_GG", "0") == "1"
    USE_ENHANCED_ZBAR = os.getenv("USE_ENHANCED_ZBAR", "0") == "1"
    
    decoders = []
    
    # Add ZBar decoder (enhanced or standard)
    if USE_ENHANCED_ZBAR and HAS_ENHANCED_ZBAR:
        print(f"⚡ Using EnhancedZBarDecoder")
        decoders.append(EnhancedZBarDecoder())
    else:
        decoders.append(ZBarDecoder())
    
    # Add other decoders
    decoders.extend([OpenCvQrDecoder(), VisionDecoder()])
    
    # Add GG label decoder (improved or standard)
    if USE_IMPROVED_GG and HAS_IMPROVED_GG:
        print(f"⚡ Using ImprovedGGLabelDecoder")
        decoders.append(ImprovedGGLabelDecoder())
    else:
        decoders.append(GGLabelDecoder())
    
    pipeline = DecoderPipeline(decoders)
    
    print(f"\n{'='*70}")
    
    results = []
    for idx, img_path in enumerate(sorted(image_files), 1):
        print(f"\n[{idx}/{len(image_files)}] {img_path.name}")
        result = evaluate_image(pipeline, str(img_path))
        
        if result['success']:
            print(f"  ⏱️  Time: {result['total_time_ms']}ms")
            print(f"  📊 Results: {result['total_results']} total")
            if result['gg_labels']:
                print(f"  🏷️  GG: {', '.join(result['gg_labels'])}")
            if result['q_codes']:
                print(f"  🔢 Q: {', '.join(result['q_codes'])}")
            if result['regular_barcodes']:
                print(f"  📦 Barcodes: {', '.join(result['regular_barcodes'][:3])}" + 
                      (f" +{len(result['regular_barcodes'])-3} more" if len(result['regular_barcodes']) > 3 else ""))
            
            # Show decoder breakdown
            for t in result['timeline']:
                if t['count'] > 0:
                    print(f"    • {t['decoder']}: {t['count']} codes in {t['ms']}ms")
        else:
            print(f"  ❌ Error: {result['error']}")
        
        results.append(result)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"\n📈 SUMMARY")
    print(f"{'='*70}")
    
    successful = [r for r in results if r['success']]
    total_gg = sum(len(r['gg_labels']) for r in successful)
    total_q = sum(len(r['q_codes']) for r in successful)
    total_barcodes = sum(len(r['regular_barcodes']) for r in successful)
    avg_time = sum(r['total_time_ms'] for r in successful) / len(successful) if successful else 0
    
    images_with_gg = sum(1 for r in successful if r['gg_labels'])
    images_with_q = sum(1 for r in successful if r['q_codes'])
    images_with_both = sum(1 for r in successful if r['gg_labels'] and r['q_codes'])
    
    print(f"Images processed: {len(successful)}/{len(results)}")
    print(f"Average time: {avg_time:.0f}ms")
    print(f"\nDetection results:")
    print(f"  • GG labels: {total_gg} ({images_with_gg} images)")
    print(f"  • Q codes: {total_q} ({images_with_q} images)")
    print(f"  • GG+Q pairs: {images_with_both} images")
    print(f"  • Regular barcodes: {total_barcodes}")
    
    # Decoder performance
    decoder_stats = {}
    for r in successful:
        for t in r['timeline']:
            name = t['decoder']
            if name not in decoder_stats:
                decoder_stats[name] = {'count': 0, 'time': 0, 'runs': 0}
            decoder_stats[name]['count'] += t['count']
            decoder_stats[name]['time'] += t['ms']
            decoder_stats[name]['runs'] += 1
    
    print(f"\nDecoder performance:")
    for name, stats in decoder_stats.items():
        avg = stats['time'] / stats['runs'] if stats['runs'] > 0 else 0
        print(f"  • {name}: {stats['count']} codes, avg {avg:.0f}ms/image")
    
    # Save results
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == '.json':
            with open(output_path, 'w') as f:
                json.dump({
                    'summary': {
                        'total_images': len(results),
                        'successful': len(successful),
                        'avg_time_ms': avg_time,
                        'total_gg': total_gg,
                        'total_q': total_q,
                        'total_barcodes': total_barcodes,
                        'images_with_gg': images_with_gg,
                        'images_with_q': images_with_q,
                        'images_with_both': images_with_both
                    },
                    'decoder_stats': decoder_stats,
                    'results': results
                }, f, indent=2)
            print(f"\n💾 Saved detailed results to {output_path}")
        
        elif output_path.suffix == '.csv':
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Image', 'Time(ms)', 'GG', 'Q', 'Barcodes', 'Total'])
                for r in successful:
                    writer.writerow([
                        r['image'],
                        r['total_time_ms'],
                        ','.join(r['gg_labels']),
                        ','.join(r['q_codes']),
                        ','.join(r['regular_barcodes']),
                        r['total_results']
                    ])
            print(f"\n💾 Saved CSV to {output_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate decoder pipeline performance')
    parser.add_argument('test_dir', help='Directory containing test images')
    parser.add_argument('-o', '--output', help='Output file (JSON or CSV)')
    parser.add_argument('--baseline', action='store_true', help='Save as baseline for comparison')
    
    args = parser.parse_args()
    
    output_file = args.output
    if args.baseline and not output_file:
        output_file = 'eval_results/baseline.json'
    
    run_evaluation(args.test_dir, output_file)

