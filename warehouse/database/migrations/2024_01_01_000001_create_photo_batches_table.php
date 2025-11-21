<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('photo_batches', function (Blueprint $table) {
            $table->id();
            $table->string('correlation_id', 32)->unique();
            $table->bigInteger('chat_id');
            $table->enum('status', ['pending', 'processing', 'completed', 'failed'])->default('pending');
            $table->json('gg_labels')->nullable();
            $table->json('barcodes')->nullable();
            $table->boolean('sent_to_pochtoy')->default(false);
            $table->json('pochtoy_response')->nullable();
            $table->timestamps();

            $table->index('chat_id');
            $table->index('status');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('photo_batches');
    }
};
