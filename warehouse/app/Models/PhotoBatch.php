<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class PhotoBatch extends Model
{
    protected $fillable = [
        'correlation_id',
        'chat_id',
        'status',
        'gg_labels',
        'barcodes',
        'sent_to_pochtoy',
        'pochtoy_response',
    ];

    protected $casts = [
        'gg_labels' => 'array',
        'barcodes' => 'array',
        'pochtoy_response' => 'array',
        'sent_to_pochtoy' => 'boolean',
    ];

    public function photos(): HasMany
    {
        return $this->hasMany(Photo::class, 'batch_id')->orderBy('order');
    }

    public function getGgLabels(): array
    {
        return $this->gg_labels ?? [];
    }

    public function getAllBarcodes(): array
    {
        return $this->barcodes ?? [];
    }

    public function getTrackings(): array
    {
        return array_unique(array_merge($this->getGgLabels(), $this->getAllBarcodes()));
    }
}
