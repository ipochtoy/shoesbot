<?php

namespace App\Console\Commands;

use App\Services\Decoders\ZBarDecoder;
use App\Services\Decoders\GeminiDecoder;
use App\Services\Decoders\OpenAIDecoder;
use Illuminate\Console\Command;

class TestDecoders extends Command
{
    protected $signature = 'bot:test-decoders {image : Path to test image}';
    protected $description = 'Test decoder speeds on an image';

    public function handle(): int
    {
        $imagePath = $this->argument('image');

        if (!file_exists($imagePath)) {
            $this->error("File not found: {$imagePath}");
            return 1;
        }

        $this->info("Testing decoders on: {$imagePath}\n");

        $decoders = [
            'ZBar' => new ZBarDecoder(),
            'Gemini Flash' => new GeminiDecoder(),
            'OpenAI GPT-4o-mini' => new OpenAIDecoder(),
        ];

        $results = [];

        foreach ($decoders as $name => $decoder) {
            $this->info("Testing {$name}...");

            $start = microtime(true);
            try {
                $decoded = $decoder->decode($imagePath);
                $elapsed = round((microtime(true) - $start) * 1000);

                $codes = array_map(fn($r) => $r->data, $decoded);
                $results[$name] = [
                    'time_ms' => $elapsed,
                    'count' => count($decoded),
                    'codes' => $codes,
                ];

                $this->info("  Time: {$elapsed}ms");
                $this->info("  Found: " . count($decoded) . " codes");
                if ($codes) {
                    $this->info("  Codes: " . implode(', ', $codes));
                }

            } catch (\Exception $e) {
                $elapsed = round((microtime(true) - $start) * 1000);
                $results[$name] = [
                    'time_ms' => $elapsed,
                    'count' => 0,
                    'error' => $e->getMessage(),
                ];
                $this->error("  Error: " . $e->getMessage());
            }

            $this->newLine();
        }

        // Summary table
        $this->info("=== Summary ===\n");
        $this->table(
            ['Decoder', 'Time (ms)', 'Codes Found'],
            array_map(fn($name, $r) => [
                $name,
                $r['time_ms'],
                $r['count'] . ($r['error'] ?? '' ? ' (error)' : ''),
            ], array_keys($results), $results)
        );

        // Recommendation
        $fastest = array_keys($results)[0];
        $fastestTime = PHP_INT_MAX;

        foreach ($results as $name => $r) {
            if ($r['count'] > 0 && $r['time_ms'] < $fastestTime) {
                $fastest = $name;
                $fastestTime = $r['time_ms'];
            }
        }

        $this->newLine();
        $this->info("Recommended: {$fastest} ({$fastestTime}ms)");

        return 0;
    }
}
