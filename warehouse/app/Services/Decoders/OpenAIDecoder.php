<?php

namespace App\Services\Decoders;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class OpenAIDecoder
{
    public string $name = 'openai';

    public function decode(string $imagePath): array
    {
        $apiKey = config('services.openai.api_key');
        if (!$apiKey) {
            return [];
        }

        $results = [];

        try {
            $imageData = base64_encode(file_get_contents($imagePath));

            $response = Http::timeout(15)
                ->withHeaders(['Authorization' => "Bearer {$apiKey}"])
                ->post('https://api.openai.com/v1/chat/completions', [
                    'model' => 'gpt-4o-mini',
                    'messages' => [
                        [
                            'role' => 'user',
                            'content' => [
                                [
                                    'type' => 'text',
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
                                    'type' => 'image_url',
                                    'image_url' => [
                                        'url' => "data:image/jpeg;base64,{$imageData}"
                                    ]
                                ]
                            ]
                        ]
                    ],
                    'max_tokens' => 50,
                    'temperature' => 0
                ]);

            if ($response->successful()) {
                $text = strtoupper($response->json('choices.0.message.content', ''));
                Log::debug("OpenAI response: {$text}");

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
            Log::error("OpenAI decoder error: " . $e->getMessage());
        }

        return $results;
    }
}
