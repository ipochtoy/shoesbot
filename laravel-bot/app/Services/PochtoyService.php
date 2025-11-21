<?php

namespace App\Services;

use App\Models\PhotoBatch;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class PochtoyService
{
    private string $apiUrl;
    private string $apiToken;

    public function __construct()
    {
        $this->apiUrl = config('services.pochtoy.api_url');
        $this->apiToken = config('services.pochtoy.api_token');
    }

    public function sendBatch(PhotoBatch $batch): array
    {
        try {
            // Collect images
            $images = [];
            foreach ($batch->photos as $idx => $photo) {
                try {
                    $imageData = $photo->getImageData();
                    $images[] = [
                        'base64' => base64_encode($imageData),
                        'file_name' => "{$batch->correlation_id}_{$idx}.jpg",
                    ];
                } catch (\Exception $e) {
                    Log::error("Error encoding photo {$photo->id}: " . $e->getMessage());
                }
            }

            // Collect trackings
            $trackings = $batch->getTrackings();

            Log::info("Sending to Pochtoy: " . count($images) . " images, " . count($trackings) . " trackings");

            // Send to Pochtoy
            $response = Http::timeout(60)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                    'Authorization' => "Bearer {$this->apiToken}",
                ])
                ->put($this->apiUrl, [
                    'images' => $images,
                    'trackings' => $trackings,
                ]);

            Log::info("Pochtoy response: " . $response->status());

            if ($response->status() === 400) {
                return [
                    'success' => false,
                    'error' => $response->json('message', 'Unknown error'),
                ];
            }

            if ($response->successful()) {
                $result = $response->json();
                if (($result['status'] ?? '') === 'ok') {
                    return [
                        'success' => true,
                        'message' => 'Product added successfully',
                        'images_sent' => count($images),
                        'trackings_sent' => count($trackings),
                    ];
                }
                return [
                    'success' => false,
                    'error' => $result['message'] ?? 'Pochtoy error',
                ];
            }

            return [
                'success' => false,
                'error' => "HTTP error: " . $response->status(),
            ];

        } catch (\Exception $e) {
            Log::error("Pochtoy error: " . $e->getMessage());
            return [
                'success' => false,
                'error' => $e->getMessage(),
            ];
        }
    }

    public function delete(array $trackings): array
    {
        try {
            $deleteUrl = str_replace('/store', '/delete', $this->apiUrl);

            $response = Http::timeout(30)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                    'Authorization' => "Bearer {$this->apiToken}",
                ])
                ->post($deleteUrl, [
                    'trackings' => array_unique($trackings),
                ]);

            if ($response->successful()) {
                return ['success' => true, 'message' => 'Deleted from Pochtoy'];
            }

            return ['success' => false, 'error' => "HTTP " . $response->status()];

        } catch (\Exception $e) {
            return ['success' => false, 'error' => $e->getMessage()];
        }
    }
}
