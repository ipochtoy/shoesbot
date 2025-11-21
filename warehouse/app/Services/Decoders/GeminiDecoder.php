<?php

namespace App\Services\Decoders;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class GeminiDecoder
{
    public string $name = 'gemini';

    public function decode(string $imagePath): array
    {
        $apiKey = config('services.gemini.api_key');
        if (!$apiKey) {
            return [];
        }

        $results = [];

        try {
            $imageData = base64_encode(file_get_contents($imagePath));
            $mimeType = mime_content_type($imagePath) ?: 'image/jpeg';

            $response = Http::timeout(15)->post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={$apiKey}",
                [
                    'contents' => [
                        [
                            'parts' => [
                                [
                                    'text' => 'Find ALL codes on this product:

1. GG code - LARGE BLACK TEXT on yellow sticker (like GG727, GG681)
2. Q code - numbers UNDER or NEAR the barcode lines (like Q2622988, Q747)

IMPORTANT:
- Q code is usually 7-10 digits starting with Q
- Look UNDER the barcode stripes
- Q code can be small text
- Check EVERY corner and label

Return ALL codes found, one per line:
GG727
Q2622988

If you find only GG, still return it.
If no codes at all, return "NONE"'
                                ],
                                [
                                    'inline_data' => [
                                        'mime_type' => $mimeType,
                                        'data' => $imageData,
                                    ]
                                ]
                            ]
                        ]
                    ],
                    'generationConfig' => [
                        'temperature' => 0,
                        'maxOutputTokens' => 100,
                    ]
                ]
            );

            if ($response->successful()) {
                $text = strtoupper($response->json('candidates.0.content.parts.0.text', ''));
                Log::debug("Gemini response: {$text}");

                // Parse GG and Q codes
                preg_match_all('/\b(GG\d{2,7})\b/', $text, $ggMatches);
                preg_match_all('/\b(Q\d{4,10})\b/', $text, $qMatches);

                foreach ($ggMatches[1] as $match) {
                    $results[] = new BarcodeResult('GG_LABEL', $match, $this->name);
                }
                foreach ($qMatches[1] as $match) {
                    $results[] = new BarcodeResult('GG_LABEL', $match, $this->name);
                }
            }
        } catch (\Exception $e) {
            Log::error("Gemini decoder error: " . $e->getMessage());
        }

        return $results;
    }
}
