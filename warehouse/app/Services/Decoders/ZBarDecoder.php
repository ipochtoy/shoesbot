<?php

namespace App\Services\Decoders;

use Illuminate\Support\Facades\Log;

class ZBarDecoder
{
    public string $name = 'zbar';

    public function decode(string $imagePath): array
    {
        $results = [];

        // Use zbarimg CLI tool (brew install zbar on macOS)
        $output = [];
        $returnVar = 0;

        exec("zbarimg -q --raw " . escapeshellarg($imagePath) . " 2>/dev/null", $output, $returnVar);

        foreach ($output as $line) {
            $line = trim($line);
            if (empty($line)) continue;

            // Parse format: TYPE:DATA or just DATA
            if (strpos($line, ':') !== false) {
                [$symbology, $data] = explode(':', $line, 2);
            } else {
                $symbology = 'UNKNOWN';
                $data = $line;
            }

            $results[] = new BarcodeResult($symbology, $data, $this->name);
        }

        Log::debug("ZBar decoded: " . count($results) . " barcodes");
        return $results;
    }
}
