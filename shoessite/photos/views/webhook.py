"""
Webhook views - обработка вебхуков от внешних сервисов (Pochtoy).
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os


@csrf_exempt
@require_http_methods(["POST"])
def pochtoy_webhook(request):
    """Webhook для приема сигналов от Pochtoy."""
    try:
        data = json.loads(request.body)
        print(f"Received Pochtoy webhook: {data}")

        # ID чата админа для уведомлений (из .env или по умолчанию)
        admin_chat_id = int(os.getenv('ADMIN_CHAT_ID', '0'))

        if not admin_chat_id:
            # Если не настроен - просто логируем
            print("ADMIN_CHAT_ID not set, webhook logged but not sent to Telegram")
            return JsonResponse({'success': True, 'message': 'Logged'})

        from ..pochtoy_webhook import handle_pochtoy_webhook
        result = handle_pochtoy_webhook(data, admin_chat_id)

        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
