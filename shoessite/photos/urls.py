from django.urls import path
from . import views

urlpatterns = [
    path('api/upload-batch/', views.upload_batch, name='upload_batch'),
    path('api/buffer-upload/', views.buffer_upload, name='buffer_upload'),
    path('api/pochtoy-webhook/', views.pochtoy_webhook, name='pochtoy_webhook'),
    path('sorting/', views.sorting_view, name='sorting_view'),
    path('api/update-photo-group/<int:photo_id>/', views.update_photo_group, name='update_photo_group'),
    path('api/send-group-to-bot/<int:group_id>/', views.send_group_to_bot, name='send_group_to_bot'),
    path('api/detect-gg-in-buffer/', views.detect_gg_in_buffer, name='detect_gg_in_buffer'),
    path('api/clear-buffer/', views.clear_buffer, name='clear_buffer'),
    path('api/send-group-to-pochtoy/<int:group_id>/', views.send_group_to_pochtoy, name='send_group_to_pochtoy'),
    path('api/delete-card-by-correlation/<str:correlation_id>/', views.delete_card_by_correlation, name='delete_card_by_correlation'),
    path('api/delete-buffer-photo/<int:photo_id>/', views.delete_buffer_photo, name='delete_buffer_photo'),
    path('api/get-last-card/', views.get_last_card, name='get_last_card'),
    path('admin/process-task/<int:task_id>/', views.process_task, name='process_task'),
    path('card/<int:card_id>/', views.product_card_detail, name='product_card_detail'),
    path('api/search-barcode/', views.search_by_barcode, name='search_by_barcode'),
    path('api/reprocess-photo/<int:photo_id>/', views.reprocess_photo, name='reprocess_photo'),
    path('api/generate-from-instruction/<int:card_id>/', views.generate_from_instruction_api, name='generate_from_instruction'),
    path('api/generate-summary/<int:card_id>/', views.generate_summary_api, name='generate_summary'),
    path('api/search-stock-photos/<int:card_id>/', views.search_stock_photos_api, name='search_stock_photos'),
    path('api/upload-photo-from-computer/<int:card_id>/', views.upload_photo_from_computer, name='upload_photo_from_computer'),
    path('api/add-photo-from-url/<int:card_id>/', views.add_photo_from_url, name='add_photo_from_url'),
    path('api/set-main-photo/<int:photo_id>/', views.set_main_photo, name='set_main_photo'),
    path('api/move-photo/<int:photo_id>/', views.move_photo, name='move_photo'),
    path('api/delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    path('api/rotate-photo/<int:photo_id>/', views.rotate_photo, name='rotate_photo'),
    path('api/save-ai-summary/<int:card_id>/', views.save_ai_summary, name='save_ai_summary'),
    path('api/enhance-photo/<int:photo_id>/', views.enhance_photo, name='enhance_photo'),
    path('api/add-barcode/<int:card_id>/', views.add_barcode_manually, name='add_barcode_manually'),
]

