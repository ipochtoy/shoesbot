<?php

namespace App\Services;

use App\Services\Decoders\BarcodeResult;
use App\Services\Decoders\ZBarDecoder;
use App\Services\Decoders\GeminiDecoder;
use App\Services\Decoders\OpenAIDecoder;
use Illuminate\Support\Facades\Log;

class DecoderPipeline
{
    private array $quickDecoders;
    private array $aiDecoders;

    public function __construct()
    {
        $this->quickDecoders = [
            new ZBarDecoder(),
        ];

        // Prefer Gemini (faster, cheaper), fallback to OpenAI
        $this->aiDecoders = [
            new GeminiDecoder(),
            new OpenAIDecoder(),
        ];
    }

    public function process(string $imagePath): array
    {
        $results = [];
        $seen = [];
        $timeline = [];

        // Step 1: Quick decoders (ZBar)
        foreach ($this->quickDecoders as $decoder) {
            $start = microtime(true);
            try {
                $decoded = $decoder->decode($imagePath);
                foreach ($decoded as $barcode) {
                    $key = $barcode->symbology . ':' . $barcode->data;
                    if (!isset($seen[$key])) {
                        $seen[$key] = true;
                        $results[] = $barcode;
                    }
                }
            } catch (\Exception $e) {
                Log::error("Decoder {$decoder->name} error: " . $e->getMessage());
            }
            $timeline[] = [
                'decoder' => $decoder->name,
                'ms' => round((microtime(true) - $start) * 1000),
                'count' => count($decoded ?? []),
            ];
        }

        // Step 2: Check if we have GG labels from quick decoders
        $hasGG = $this->hasGGLabel($results);
        $hasQ = $this->hasQCode($results);

        // Step 3: If missing GG or Q, use AI decoders
        if (!$hasGG || !$hasQ) {
            Log::info("Missing GG={$hasGG} Q={$hasQ}, trying AI decoders");

            foreach ($this->aiDecoders as $decoder) {
                $start = microtime(true);
                try {
                    $decoded = $decoder->decode($imagePath);
                    $count = 0;
                    foreach ($decoded as $barcode) {
                        $key = $barcode->symbology . ':' . $barcode->data;
                        if (!isset($seen[$key])) {
                            $seen[$key] = true;
                            $results[] = $barcode;
                            $count++;
                        }
                    }
                    $timeline[] = [
                        'decoder' => $decoder->name,
                        'ms' => round((microtime(true) - $start) * 1000),
                        'count' => $count,
                    ];

                    // If found GG+Q pair, stop
                    if ($this->hasGGLabel($results) && $this->hasQCode($results)) {
                        break;
                    }
                } catch (\Exception $e) {
                    Log::error("AI Decoder {$decoder->name} error: " . $e->getMessage());
                }
            }
        }

        return [
            'results' => $results,
            'timeline' => $timeline,
        ];
    }

    private function hasGGLabel(array $results): bool
    {
        foreach ($results as $r) {
            if (str_starts_with($r->data, 'GG')) {
                return true;
            }
        }
        return false;
    }

    private function hasQCode(array $results): bool
    {
        foreach ($results as $r) {
            if (str_starts_with($r->data, 'Q') && strlen($r->data) > 4) {
                return true;
            }
        }
        return false;
    }
}
