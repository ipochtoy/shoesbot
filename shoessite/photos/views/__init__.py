"""
Views модуль - разбит на логические компоненты.
Этот файл обеспечивает обратную совместимость со старым монолитным views.py.

Структура:
- upload.py: загрузка фото (upload_batch, upload_photo_from_computer, add_photo_from_url, buffer_upload)
- photos.py: управление фото (set_main_photo, move_photo, delete_photo, rotate_photo)
- ai.py: AI функции (generate_summary_api, generate_from_instruction_api, save_ai_summary)
- search.py: поиск товаров и баркодов (search_by_barcode, search_stock_photos_api, и др.)
- barcodes.py: обработка баркодов (reprocess_photo, add_barcode_manually)
- admin.py: админские функции (product_card_detail, process_task)
- buffer.py: работа с буфером сортировки (sorting_view, detect_gg_in_buffer, и др.)
- webhook.py: вебхуки (pochtoy_webhook)
- enhance.py: улучшение фото через FASHN (enhance_photo)
"""

# Upload views
from .upload import (
    upload_batch,
    upload_photo_from_computer,
    add_photo_from_url,
    buffer_upload,
)

# Photo management
from .photos import (
    set_main_photo,
    move_photo,
    delete_photo,
    rotate_photo,
)

# AI views
from .ai import (
    generate_summary_api,
    generate_from_instruction_api,
    save_ai_summary,
)

# Search views
from .search import (
    search_by_barcode,
    search_stock_photos_api,
    # Helper functions (также экспортируем для совместимости)
    search_google_images,
    search_google_images_web,
    search_with_google_lens,
    search_product_with_vision_api,
    search_bing_images,
    search_product_info,
    search_stock_photos,
)

# Barcode views
from .barcodes import (
    reprocess_photo,
    add_barcode_manually,
    # Helper functions
    process_with_google_vision_direct,
    process_with_openai_vision,
)

# Admin views
from .admin import (
    product_card_detail,
    process_task,
    # Helper functions
    process_google_vision,
    process_azure_cv,
)

# Buffer views
from .buffer import (
    sorting_view,
    update_photo_group,
    send_group_to_bot,
    detect_gg_in_buffer,
    send_group_to_pochtoy,
    clear_buffer,
    delete_card_by_correlation,
    get_last_card,
    delete_buffer_photo,
)

# Webhook views
from .webhook import (
    pochtoy_webhook,
)

# Enhance views
from .enhance import (
    enhance_photo,
)

# Все экспортируемые функции для __all__
__all__ = [
    # Upload
    'upload_batch',
    'upload_photo_from_computer',
    'add_photo_from_url',
    'buffer_upload',
    # Photos
    'set_main_photo',
    'move_photo',
    'delete_photo',
    'rotate_photo',
    # AI
    'generate_summary_api',
    'generate_from_instruction_api',
    'save_ai_summary',
    # Search
    'search_by_barcode',
    'search_stock_photos_api',
    'search_google_images',
    'search_google_images_web',
    'search_with_google_lens',
    'search_product_with_vision_api',
    'search_bing_images',
    'search_product_info',
    'search_stock_photos',
    # Barcodes
    'reprocess_photo',
    'add_barcode_manually',
    'process_with_google_vision_direct',
    'process_with_openai_vision',
    # Admin
    'product_card_detail',
    'process_task',
    'process_google_vision',
    'process_azure_cv',
    # Buffer
    'sorting_view',
    'update_photo_group',
    'send_group_to_bot',
    'detect_gg_in_buffer',
    'send_group_to_pochtoy',
    'clear_buffer',
    'delete_card_by_correlation',
    'get_last_card',
    'delete_buffer_photo',
    # Webhook
    'pochtoy_webhook',
    # Enhance
    'enhance_photo',
]
