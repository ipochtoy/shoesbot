<?php

namespace App\Console\Commands;

use App\Models\Photo;
use App\Models\PhotoBatch;
use App\Services\DecoderPipeline;
use App\Services\PochtoyService;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class TelegramBot extends Command
{
    protected $signature = 'bot:run';
    protected $description = 'Run Telegram bot with long polling';

    private string $token;
    private string $apiUrl;
    private array $photoBuffer = [];
    private array $bufferTimers = [];
    private int $bufferTimeout;
    private int $bufferMax;
    private DecoderPipeline $pipeline;
    private PochtoyService $pochtoy;

    public function handle(): int
    {
        $this->token = config('services.telegram.bot_token');
        if (!$this->token) {
            $this->error('TELEGRAM_BOT_TOKEN not set!');
            return 1;
        }

        $this->apiUrl = "https://api.telegram.org/bot{$this->token}";
        $this->bufferTimeout = (int) config('services.telegram.buffer_timeout', 3);
        $this->bufferMax = (int) config('services.telegram.buffer_max', 10);
        $this->pipeline = new DecoderPipeline();
        $this->pochtoy = new PochtoyService();

        $this->info('Bot started. Listening for updates...');

        $offset = 0;
        while (true) {
            try {
                $updates = $this->getUpdates($offset);

                foreach ($updates as $update) {
                    $offset = $update['update_id'] + 1;
                    $this->processUpdate($update);
                }

                // Process expired buffers
                $this->processExpiredBuffers();

                usleep(100000); // 100ms

            } catch (\Exception $e) {
                Log::error('Bot error: ' . $e->getMessage());
                $this->error('Error: ' . $e->getMessage());
                sleep(5);
            }
        }

        return 0;
    }

    private function getUpdates(int $offset): array
    {
        $response = Http::timeout(30)->get("{$this->apiUrl}/getUpdates", [
            'offset' => $offset,
            'timeout' => 25,
            'allowed_updates' => ['message', 'callback_query'],
        ]);

        return $response->json('result', []);
    }

    private function processUpdate(array $update): void
    {
        if (isset($update['message'])) {
            $this->processMessage($update['message']);
        } elseif (isset($update['callback_query'])) {
            $this->processCallback($update['callback_query']);
        }
    }

    private function processMessage(array $message): void
    {
        $chatId = $message['chat']['id'];

        // Handle commands
        if (isset($message['text'])) {
            $text = $message['text'];
            if ($text === '/start') {
                $this->sendMessage($chatId, "Send photos, I'll extract barcodes/QR. /ping - check.");
                return;
            }
            if ($text === '/ping') {
                $this->sendMessage($chatId, 'pong');
                return;
            }
        }

        // Handle photos
        if (isset($message['photo'])) {
            $this->handlePhoto($chatId, $message);
        }
    }

    private function handlePhoto(int $chatId, array $message): void
    {
        $photo = end($message['photo']); // Largest size
        $fileId = $photo['file_id'];
        $messageId = $message['message_id'];

        // Initialize buffer for chat
        if (!isset($this->photoBuffer[$chatId])) {
            $this->photoBuffer[$chatId] = [];
            $this->bufferTimers[$chatId] = time();
            $this->sendMessage($chatId, "Processing...");
        }

        // Add to buffer
        $this->photoBuffer[$chatId][] = [
            'file_id' => $fileId,
            'message_id' => $messageId,
        ];

        Log::info("Photo added to buffer for chat {$chatId}, count: " . count($this->photoBuffer[$chatId]));

        // Check if buffer is full
        if (count($this->photoBuffer[$chatId]) >= $this->bufferMax) {
            $this->processBuffer($chatId);
        }
    }

    private function processExpiredBuffers(): void
    {
        $now = time();
        foreach ($this->bufferTimers as $chatId => $startTime) {
            if ($now - $startTime >= $this->bufferTimeout) {
                $this->processBuffer($chatId);
            }
        }
    }

    private function processBuffer(int $chatId): void
    {
        if (!isset($this->photoBuffer[$chatId]) || empty($this->photoBuffer[$chatId])) {
            return;
        }

        $photos = $this->photoBuffer[$chatId];
        unset($this->photoBuffer[$chatId], $this->bufferTimers[$chatId]);

        Log::info("Processing batch of " . count($photos) . " photos for chat {$chatId}");

        try {
            // Create batch
            $correlationId = Str::random(8);
            $batch = PhotoBatch::create([
                'correlation_id' => $correlationId,
                'chat_id' => $chatId,
                'status' => 'processing',
            ]);

            $allResults = [];
            $allTimelines = [];

            // Download and process each photo
            foreach ($photos as $idx => $photoData) {
                $fileId = $photoData['file_id'];

                // Get file path from Telegram
                $fileInfo = Http::get("{$this->apiUrl}/getFile", ['file_id' => $fileId])->json('result');
                $filePath = $fileInfo['file_path'];

                // Download file
                $fileUrl = "https://api.telegram.org/file/bot{$this->token}/{$filePath}";
                $imageData = Http::get($fileUrl)->body();

                // Save locally
                $localPath = "photos/{$correlationId}_{$idx}.jpg";
                $fullPath = storage_path("app/{$localPath}");

                if (!is_dir(dirname($fullPath))) {
                    mkdir(dirname($fullPath), 0755, true);
                }
                file_put_contents($fullPath, $imageData);

                // Create photo record
                $batch->photos()->create([
                    'file_id' => $fileId,
                    'path' => $localPath,
                    'order' => $idx,
                    'is_main' => $idx === 0,
                ]);

                // Run decoder pipeline
                $result = $this->pipeline->process($fullPath);
                $allResults = array_merge($allResults, $result['results']);
                $allTimelines = array_merge($allTimelines, $result['timeline']);
            }

            // Extract GG labels and barcodes
            $ggLabels = [];
            $barcodes = [];

            foreach ($allResults as $r) {
                if ($r->symbology === 'GG_LABEL' || str_starts_with($r->data, 'GG') || str_starts_with($r->data, 'Q')) {
                    $ggLabels[] = $r->data;
                } else {
                    $barcodes[] = $r->data;
                }
            }

            $batch->update([
                'gg_labels' => array_unique($ggLabels),
                'barcodes' => array_unique($barcodes),
            ]);

            // Check for GG pair
            $hasGG = !empty(array_filter($ggLabels, fn($l) => str_starts_with($l, 'GG')));
            $hasQ = !empty(array_filter($ggLabels, fn($l) => str_starts_with($l, 'Q')));

            if (!$hasGG && !$hasQ) {
                // No GG label found
                $this->sendMessage($chatId, "No GG label found!\n\nCannot create card without GG code.", [
                    'reply_markup' => json_encode([
                        'inline_keyboard' => [[
                            ['text' => 'Delete all', 'callback_data' => "del:{$correlationId}"]
                        ]]
                    ])
                ]);
                $batch->update(['status' => 'failed']);
                return;
            }

            // Send to Pochtoy
            $pochtoyResult = $this->pochtoy->sendBatch($batch);

            $batch->update([
                'sent_to_pochtoy' => $pochtoyResult['success'],
                'pochtoy_response' => $pochtoyResult,
                'status' => 'completed',
            ]);

            // Build response message
            $statusEmoji = ($hasGG && $hasQ) ? '' : '';
            $message = "{$statusEmoji} <b>GG label " . ($hasGG && $hasQ ? 'found (complete pair)' : 'incomplete') . "</b>\n";

            if ($hasGG) {
                $ggCodes = array_filter($ggLabels, fn($l) => str_starts_with($l, 'GG'));
                $message .= "GG: " . implode(', ', $ggCodes) . "\n";
            }
            if ($hasQ) {
                $qCodes = array_filter($ggLabels, fn($l) => str_starts_with($l, 'Q'));
                $message .= "Q: " . implode(', ', $qCodes) . "\n";
            }

            $message .= "\nPhotos: " . count($photos);

            if ($pochtoyResult['success']) {
                $message .= "\n\nSent to Pochtoy";
            } else {
                $message .= "\n\nPochtoy error: " . ($pochtoyResult['error'] ?? 'unknown');
            }

            // Timeline info
            $timelineStr = implode(' | ', array_map(
                fn($t) => "{$t['decoder']}: {$t['count']} in {$t['ms']}ms",
                $allTimelines
            ));
            $message .= "\n\n<code>{$timelineStr}</code>";

            $this->sendMessage($chatId, $message, [
                'parse_mode' => 'HTML',
                'reply_markup' => json_encode([
                    'inline_keyboard' => [[
                        ['text' => 'Retry', 'callback_data' => "retry:{$correlationId}"],
                        ['text' => 'Delete', 'callback_data' => "del:{$correlationId}"]
                    ]]
                ])
            ]);

            Log::info("Batch {$correlationId} completed");

        } catch (\Exception $e) {
            Log::error("Process buffer error: " . $e->getMessage());
            $this->sendMessage($chatId, "Error: " . $e->getMessage());
        }
    }

    private function processCallback(array $callback): void
    {
        $chatId = $callback['message']['chat']['id'];
        $data = $callback['data'];
        $callbackId = $callback['id'];

        // Answer callback
        Http::post("{$this->apiUrl}/answerCallbackQuery", ['callback_query_id' => $callbackId]);

        if (str_starts_with($data, 'del:')) {
            $correlationId = substr($data, 4);
            $batch = PhotoBatch::where('correlation_id', $correlationId)->first();

            if ($batch) {
                // Delete from Pochtoy
                $this->pochtoy->delete($batch->getTrackings());

                // Delete local files
                foreach ($batch->photos as $photo) {
                    @unlink($photo->getFullPath());
                }

                // Delete from DB
                $batch->delete();

                $this->sendMessage($chatId, "Deleted: batch {$correlationId}");
            }
        } elseif (str_starts_with($data, 'retry:')) {
            $correlationId = substr($data, 6);
            // TODO: Implement retry logic
            $this->sendMessage($chatId, "Retry not implemented yet");
        }
    }

    private function sendMessage(int $chatId, string $text, array $extra = []): void
    {
        Http::post("{$this->apiUrl}/sendMessage", array_merge([
            'chat_id' => $chatId,
            'text' => $text,
        ], $extra));
    }
}
