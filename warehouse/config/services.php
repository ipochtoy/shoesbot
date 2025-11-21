<?php

return [
    'telegram' => [
        'bot_token' => env('TELEGRAM_BOT_TOKEN'),
        'buffer_timeout' => env('PHOTO_BUFFER_TIMEOUT', 3),
        'buffer_max' => env('PHOTO_BUFFER_MAX', 10),
    ],

    'pochtoy' => [
        'api_url' => env('POCHTOY_API_URL', 'https://pochtoy-test.pochtoy3.ru/api/garage-tg/store'),
        'api_token' => env('POCHTOY_API_TOKEN'),
    ],

    'openai' => [
        'api_key' => env('OPENAI_API_KEY'),
    ],

    'gemini' => [
        'api_key' => env('GEMINI_API_KEY'),
    ],

    'google_vision' => [
        'credentials' => env('GOOGLE_APPLICATION_CREDENTIALS'),
    ],
];
