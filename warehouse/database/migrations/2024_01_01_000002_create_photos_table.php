<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('photos', function (Blueprint $table) {
            $table->id();
            $table->foreignId('batch_id')->constrained('photo_batches')->onDelete('cascade');
            $table->string('file_id')->nullable();
            $table->string('path');
            $table->integer('order')->default(0);
            $table->boolean('is_main')->default(false);
            $table->timestamps();

            $table->index('batch_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('photos');
    }
};
