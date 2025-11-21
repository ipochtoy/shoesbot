<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Photo extends Model
{
    protected $fillable = [
        'batch_id',
        'file_id',
        'path',
        'order',
        'is_main',
    ];

    protected $casts = [
        'is_main' => 'boolean',
    ];

    public function batch(): BelongsTo
    {
        return $this->belongsTo(PhotoBatch::class, 'batch_id');
    }

    public function getFullPath(): string
    {
        return storage_path('app/' . $this->path);
    }

    public function getImageData(): string
    {
        return file_get_contents($this->getFullPath());
    }
}
