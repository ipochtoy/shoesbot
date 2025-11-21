<?php

namespace App\Services\Decoders;

class BarcodeResult
{
    public function __construct(
        public string $symbology,
        public string $data,
        public string $source
    ) {}

    public function toArray(): array
    {
        return [
            'symbology' => $this->symbology,
            'data' => $this->data,
            'source' => $this->source,
        ];
    }
}
