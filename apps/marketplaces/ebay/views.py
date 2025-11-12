"""
eBay marketplace DRF views.
"""
from decimal import Decimal, InvalidOperation
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404, render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import EbayCandidate, EbayToken
from .serializers import (
    EbayCandidateListSerializer,
    EbayCandidateDetailSerializer,
    BulkCreateSerializer,
    TaxonomySuggestionSerializer,
    TaxonomyCategorySerializer,
    ItemSpecificsResponseSerializer,
    PricingCompsQuerySerializer,
    PricingCompsResponseSerializer,
    PrepareResponseSerializer,
    PublishResponseSerializer,
    EndResponseSerializer,
    RepriceResponseSerializer,
    EbayTokenSerializer,
)
from .services.client import EbayClient
from .services.pricing import PricingService
from .services import pipeline
# from .tasks import prepare_candidate, publish_candidate, end_candidate, reprice_candidate  # Celery tasks disabled for now
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@method_decorator(csrf_exempt, name='dispatch')
class EbayCandidateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing eBay listing candidates.

    Endpoints:
    - GET /api/ebay/candidates/ - List all candidates
    - POST /api/ebay/candidates/ - Create a candidate
    - GET /api/ebay/candidates/{id}/ - Get candidate details
    - PUT/PATCH /api/ebay/candidates/{id}/ - Update candidate
    - DELETE /api/ebay/candidates/{id}/ - Delete candidate
    - POST /api/ebay/candidates/{id}/prepare/ - Run preparation pipeline
    - POST /api/ebay/candidates/{id}/publish/ - Publish to eBay
    - POST /api/ebay/candidates/{id}/end/ - End eBay listing
    - POST /api/ebay/candidates/{id}/reprice/ - Reprice listing
    """

    queryset = EbayCandidate.objects.select_related('photo_batch').all()
    permission_classes = [AllowAny]  # TODO: Add proper authentication
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'condition', 'heavy_flag', 'category_id']
    search_fields = ['title', 'ebay_item_id', 'photo_batch__title', 'photo_batch__sku']
    ordering_fields = ['created_at', 'updated_at', 'price_final', 'listed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use different serializers for list and detail views."""
        if self.action == 'list':
            return EbayCandidateListSerializer
        return EbayCandidateDetailSerializer

    @action(detail=True, methods=['post'])
    def prepare(self, request, pk=None):
        """
        Run AI preparation pipeline on candidate.

        POST /api/ebay/candidates/{id}/prepare/
        """
        candidate = self.get_object()

        if candidate.status == 'listed':
            return Response(
                {
                    'success': False,
                    'message': 'Cannot prepare a listed item. End it first.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Run preparation synchronously (Celery disabled for now)
        try:
            result = pipeline.prepare_candidate(candidate.id)
            
            candidate.refresh_from_db()
            
            return Response(
                {
                    'success': result.get('success', True),
                    'status': candidate.status,
                    'message': result.get('message', 'Preparation complete'),
                    'candidate': EbayCandidateDetailSerializer(candidate).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': f'Preparation failed: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def autofill(self, request, pk=None):
        """Return merged GPT + eBay data to auto-fill candidate fields."""
        candidate = self.get_object()
        raw_analysis = getattr(candidate, 'analysis_data', {})
        analysis_data = raw_analysis if isinstance(raw_analysis, dict) else {}
        openai_data = analysis_data.get('openai_latest') or {}
        google_data = analysis_data.get('google_latest') or {}
        comps_snapshot = analysis_data.get('ebay_comps_latest') or {}
        photos_snapshot = analysis_data.get('ebay_stock_photos_latest') or {}

        def pick_text(*values):
            for value in values:
                if isinstance(value, str) and value.strip():
                    return value.strip()
        def pick_first(*values):
            for value in values:
                if value not in (None, '', [], {}):
                    return value
        def coerce_price(value):
            try:
                if value is None:
                    return None
                return round(float(value), 2)
            except (TypeError, ValueError):
                return None

        price_info = comps_snapshot.get('price_info') or {}
        median_price = coerce_price(price_info.get('price') or price_info.get('total_median'))
        if median_price is None:
            median_price = coerce_price(openai_data.get('price'))
        if median_price is None:
            median_price = coerce_price(candidate.price_suggested or candidate.price_final)

        specifics = {}
        if isinstance(candidate.specifics, dict):
            specifics.update(candidate.specifics)
        for source in (google_data.get('specifics'), openai_data.get('specifics')):
            if isinstance(source, dict):
                specifics.update({k: v for k, v in source.items() if v})

        keywords = []
        seen_kw = set()
        for source in (openai_data.get('keywords'), google_data.get('keywords'), analysis_data.get('keywords')):
            if isinstance(source, list):
                for kw in source:
                    normalized = str(kw).strip()
                    if normalized and normalized.lower() not in seen_kw:
                        seen_kw.add(normalized.lower())
                        keywords.append(normalized)

        payload = {
            'title': pick_text(openai_data.get('title'), google_data.get('title'), candidate.title, candidate.photo_batch.title if candidate.photo_batch else None),
            'subtitle': pick_text(openai_data.get('subtitle'), google_data.get('subtitle')),
            'description_md': pick_text(openai_data.get('description'), google_data.get('description'), candidate.description_md),
            'condition': pick_text(openai_data.get('condition'), google_data.get('condition'), candidate.condition),
            'category_id': pick_text(openai_data.get('category_id'), google_data.get('category_id'), candidate.category_id),
            'price_recommended': median_price,
            'price_info': price_info,
            'specifics': specifics,
            'keywords': keywords,
            'search_query': pick_text(openai_data.get('search_query'), google_data.get('search_query')),
            'photo_queries': photos_snapshot.get('queries') or openai_data.get('photo_queries') or [],
            'barcodes': pick_first(openai_data.get('barcodes'), google_data.get('barcodes'), analysis_data.get('barcodes')),
            'gg_labels': pick_first(openai_data.get('gg_labels'), analysis_data.get('gg_labels')),
        }

        comps = comps_snapshot.get('items') or []
        top_comps = comps[:10]

        photos = photos_snapshot.get('items') or []
        if not photos:
            photos = comps_snapshot.get('items_photos') or []

        return Response({
            'fields': payload,
            'comps': top_comps,
            'stock_photos': photos,
            'analysis': {
                'openai': openai_data,
                'google': google_data,
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish candidate to eBay.

        POST /api/ebay/candidates/{id}/publish/
        """
        candidate = self.get_object()

        if candidate.status == 'listed':
            return Response(
                {
                    'success': False,
                    'message': 'Item is already listed on eBay.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        missing = candidate.missing_required_fields
        if missing:
            return Response(
                {
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Run publish synchronously (Celery disabled)
        try:
            result = pipeline.publish_candidate(candidate.id)
            candidate.refresh_from_db()
            
            return Response(
                {
                    'success': result.get('success', True),
                    'message': result.get('message', 'Published to eBay'),
                    'candidate': EbayCandidateDetailSerializer(candidate).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'success': False, 'message': f'Publish failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """
        End eBay listing.

        POST /api/ebay/candidates/{id}/end/
        """
        candidate = self.get_object()

        if candidate.status != 'listed':
            return Response(
                {
                    'success': False,
                    'message': 'Item is not currently listed.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not candidate.ebay_item_id:
            return Response(
                {
                    'success': False,
                    'message': 'No eBay item ID found.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Run end synchronously (Celery disabled)
        try:
            result = pipeline.end_candidate(candidate.id)
            candidate.refresh_from_db()
            
            return Response(
                {
                    'success': result.get('success', True),
                    'message': result.get('message', 'Listing ended'),
                    'candidate': EbayCandidateDetailSerializer(candidate).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'success': False, 'message': f'End failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reprice(self, request, pk=None):
        """
        Reprice listing based on current market median.

        POST /api/ebay/candidates/{id}/reprice/
        """
        candidate = self.get_object()

        if candidate.status != 'listed':
            return Response(
                {
                    'success': False,
                    'message': 'Can only reprice listed items.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Run reprice synchronously (Celery disabled)
        try:
            result = pipeline.reprice_candidate(candidate.id)
            candidate.refresh_from_db()
            
            return Response(
                {
                    'success': result.get('success', True),
                    'message': result.get('message', 'Repricing complete'),
                    'candidate': EbayCandidateDetailSerializer(candidate).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'success': False, 'message': f'Reprice failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class BulkCreateCandidatesView(APIView):
    """
    Bulk create eBay candidates from PhotoBatch IDs.

    POST /api/ebay/candidates/bulk-create/
    Body: {"photo_batch_ids": [1, 2, 3]}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidates = serializer.save()

        return Response(
            {
                'success': True,
                'created': len(candidates),
                'candidates': EbayCandidateListSerializer(candidates, many=True).data
            },
            status=status.HTTP_201_CREATED
        )


@method_decorator(csrf_exempt, name='dispatch')
class TaxonomySuggestView(APIView):
    """
    Suggest eBay categories based on query.

    GET /api/ebay/taxonomy/suggest/?q=perfume
    """
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = TaxonomySuggestionSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['q']

        # Get suggestions from eBay client
        client = EbayClient()
        suggestions = client.search_categories(query)

        return Response(
            {
                'query': query,
                'categories': suggestions
            },
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name='dispatch')
class ItemSpecificsView(APIView):
    """
    Get required item specifics for a category.

    GET /api/ebay/specifics/?category_id=12345
    """
    permission_classes = [AllowAny]

    def get(self, request):
        category_id = request.query_params.get('category_id')

        if not category_id:
            return Response(
                {'error': 'category_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get specifics from eBay client
        client = EbayClient()
        specifics = client.get_required_specifics(category_id)

        return Response(
            {
                'category_id': category_id,
                'specifics': specifics
            },
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name='dispatch')
class PricingCompsView(APIView):
    """
    Get pricing comparables from eBay marketplace.

    GET /api/ebay/pricing/comps/?q=iPhone+13
    GET /api/ebay/pricing/comps/?upc=123456789012
    """
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = PricingCompsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # Get comps from pricing service
        pricing_service = PricingService()
        result = pricing_service.get_comps(**serializer.validated_data)

        return Response(result, status=status.HTTP_200_OK)


class EbayTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing eBay OAuth tokens.

    Endpoints:
    - GET /api/ebay/tokens/ - List all tokens
    - GET /api/ebay/tokens/{id}/ - Get token details
    - POST /api/ebay/tokens/ - Create token
    - PUT/PATCH /api/ebay/tokens/{id}/ - Update token
    - DELETE /api/ebay/tokens/{id}/ - Delete token
    """

    queryset = EbayToken.objects.all()
    serializer_class = EbayTokenSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account', 'sandbox']

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """
        Refresh access token using refresh token.

        POST /api/ebay/tokens/{id}/refresh/
        """
        token = self.get_object()

        if not token.refresh_token:
            return Response(
                {'error': 'No refresh token available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Refresh token using eBay client
        client = EbayClient()
        try:
            new_token_data = client.refresh_access_token(token.refresh_token)

            token.access_token = new_token_data['access_token']
            token.expires_at = new_token_data['expires_at']
            if 'refresh_token' in new_token_data:
                token.refresh_token = new_token_data['refresh_token']
            token.save()

            return Response(
                {
                    'success': True,
                    'message': 'Token refreshed successfully',
                    'token': EbayTokenSerializer(token).data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@staff_member_required
def ebay_candidate_analyze(request, candidate_id):
    """
    Analysis page for eBay candidate - GPT analysis and data extraction.
    First step before editing.
    """
    candidate = get_object_or_404(EbayCandidate, id=candidate_id)
    photo_batch = candidate.photo_batch
    photos = photo_batch.photos.all() if photo_batch else []
    
    # Get photo data
    photo_data = []
    barcodes = []
    gg_labels = []
    
    for photo in photos:
        if photo.image:
            # Всегда используем HTTPS для медиа-URL (OpenAI не тянет http)
            request_host = request.get_host() if hasattr(request, 'get_host') else 'pochtoy.us'
            photo_url = f"https://{request_host}{photo.image.url}"
            photo_data.append({
                'id': photo.id,
                'url': photo_url,
                'is_main': photo.is_main,
                'order': photo.order,
            })
            # Collect barcodes
            for barcode in photo.barcodes.all():
                if barcode.data not in barcodes:
                    barcodes.append(barcode.data)
                # Collect GG labels (допускаем как явный source, так и распознавание по данным)
                val = (barcode.data or '').upper()
                if barcode.source == 'gg-label' or 'GG' in val or val.startswith('Q'):
                    if barcode.data not in gg_labels:
                        gg_labels.append(barcode.data)
    
    # Also get GG labels from photo batch method
    if photo_batch:
        batch_gg_labels = photo_batch.get_gg_labels()
        for label in batch_gg_labels:
            if label not in gg_labels:
                gg_labels.append(label)
    
    # Merge barcodes/GG labels from last analysis snapshot (если есть)
    try:
        analysis_snapshot = candidate.analysis_data if isinstance(candidate.analysis_data, dict) else {}
        for key in ('openai_latest', 'google_latest'):
            payload = analysis_snapshot.get(key) or {}
            if isinstance(payload, dict):
                for bc in (payload.get('barcodes') or []):
                    if bc and bc not in barcodes:
                        barcodes.append(bc)
                for gl in (payload.get('gg_labels') or []):
                    if gl and gl not in gg_labels:
                        gg_labels.append(gl)
    except Exception:
        pass
    
    # eBay comps search moved to separate endpoint (/api/ebay/search/) to avoid slow page loads
    ebay_comps = []
    
    return render(request, 'ebay/candidate_analyze.html', {
        'candidate': candidate,
        'photo_batch': photo_batch,
        'photos': photo_data,
        'barcodes': barcodes,
        'gg_labels': gg_labels,
        'ebay_comps': ebay_comps,
    })


@staff_member_required
def ebay_candidate_edit(request, candidate_id):
    """
    Edit page for eBay candidate - dedicated page for eBay listing preparation.
    """
    candidate = get_object_or_404(EbayCandidate, id=candidate_id)
    photo_batch = candidate.photo_batch
    photos = photo_batch.photos.all() if photo_batch else []
    
    # Get photo data with full Photo objects for FASHN API
    photo_data = []
    for photo in photos:
        if photo.image:
            request_scheme = request.scheme if hasattr(request, 'scheme') else 'https'
            request_host = request.get_host() if hasattr(request, 'get_host') else 'pochtoy.us'
            photo_url = f"{request_scheme}://{request_host}{photo.image.url}"
            photo_data.append({
                'id': photo.id,
                'url': photo_url,
                'is_main': photo.is_main,
                'order': photo.order,
                'photo_obj': photo,  # Full Photo object for FASHN API
            })
    
    return render(request, 'ebay/candidate_edit.html', {
        'candidate': candidate,
        'photo_batch': photo_batch,
        'photos': photo_data,
        'candidate_specifics_json': json.dumps(candidate.specifics or {}),
    })


@method_decorator(csrf_exempt, name='dispatch')
class EbaySearchView(APIView):
    """
    Search eBay for comparable listings and stock photos.
    Separate endpoint to avoid slowing down OpenAI analysis.
    
    POST /api/ebay/search/
    Body: {
        "candidate_id": 123,
        "barcode": "optional",
        "query": "optional search query"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        candidate_id = request.data.get('candidate_id')
        barcode = request.data.get('barcode')
        query = request.data.get('query')
        
        if not candidate_id:
            return Response(
                {'error': 'candidate_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        candidate = get_object_or_404(EbayCandidate, id=candidate_id)
        photo_batch = candidate.photo_batch
        
        if not photo_batch:
            return Response(
                {'error': 'No photo batch found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get barcodes from photos if not provided
        barcodes = []
        if barcode:
            barcodes = [barcode]
        else:
            photos = photo_batch.photos.all()[:10]
            for photo in photos:
                for barcode_obj in photo.barcodes.all():
                    if barcode_obj.data not in barcodes:
                        barcodes.append(barcode_obj.data)
        
        analysis_structs = []
        analysis_keywords = []
        raw_analysis = getattr(candidate, 'analysis_data', {})
        analysis_data = raw_analysis if isinstance(raw_analysis, dict) else {}
        for key in ('openai_latest', 'google_latest'):
            payload = analysis_data.get(key)
            if isinstance(payload, dict):
                analysis_structs.append(payload)
                kw = payload.get('keywords') or []
                if isinstance(kw, list):
                    analysis_keywords.extend(kw)
        for struct in analysis_structs:
            for bc in struct.get('barcodes', []) or []:
                if bc and bc not in barcodes:
                    barcodes.append(bc)

        results = {
            'comps': [],
            'stock_photos': [],
            'price_info': None,
            'analysis_keywords': [],
            'search_terms': [],
            'used_query': None,
            'strategies': [],
        }
        if analysis_keywords:
            dedup_keywords = []
            seen_kw = set()
            for kw in analysis_keywords:
                normalized = str(kw).lower()
                if normalized not in seen_kw:
                    seen_kw.add(normalized)
                    dedup_keywords.append(kw)
            results['analysis_keywords'] = dedup_keywords

        try:
            from photos.ai_helpers import search_products_on_ebay
            from apps.marketplaces.ebay.services.client import EbayClient
            from statistics import median

            ebay_client = EbayClient()
            seen_photo_urls = set()

            strategies_raw = []
            if query:
                # Если пользователь задал запрос вручную — используем только его, чтобы ускорить
                strategies_raw = [{'term': query, 'source': 'manual', 'reason': 'user input'}]
            else:
                if barcodes:
                    for bc in barcodes:
                        strategies_raw.append({'term': bc, 'source': 'barcode', 'reason': 'detected barcode'})
                for struct in analysis_structs:
                    sq = struct.get('search_query')
                    if sq:
                        strategies_raw.append({'term': sq, 'source': 'analysis', 'reason': 'summary search query'})
                    brand = struct.get('brand')
                    model = struct.get('model')
                    if brand and model:
                        strategies_raw.append({'term': f"{brand} {model}", 'source': 'analysis', 'reason': 'brand + model'})
                    elif brand:
                        strategies_raw.append({'term': brand, 'source': 'analysis', 'reason': 'brand only'})
                    keywords = struct.get('keywords') or []
                    if keywords:
                        joined = ' '.join(keywords[:6])
                        if joined:
                            strategies_raw.append({'term': joined, 'source': 'analysis', 'reason': 'top keywords'})
            # Also try candidate/batch titles to broaden search
            if getattr(candidate, 'title', None):
                strategies_raw.append({'term': candidate.title, 'source': 'candidate', 'reason': 'candidate.title'})
            if getattr(photo_batch, 'title', None):
                strategies_raw.append({'term': photo_batch.title, 'source': 'batch', 'reason': 'photo_batch.title'})

            seen_terms = set()
            strategies = []
            for entry in strategies_raw:
                term = str(entry['term']).strip()
                if not term:
                    continue
                signature = term.lower()
                if signature in seen_terms:
                    continue
                seen_terms.add(signature)
                entry['term'] = term
                strategies.append(entry)
            results['search_terms'] = [s['term'] for s in strategies]

            ebay_info = None
            if barcodes:
                try:
                    print(f"[EbaySearch] Searching eBay by barcode: {barcodes[0]}")
                    ebay_info = search_products_on_ebay(barcode=barcodes[0])
                except Exception as info_error:
                    print(f"[EbaySearch] barcode lookup failed: {info_error}")
            if not ebay_info:
                for struct in analysis_structs:
                    try:
                        ebay_info = search_products_on_ebay(
                            brand=struct.get('brand'),
                            model=struct.get('model'),
                            title=struct.get('search_query') or struct.get('title'),
                        )
                    except Exception as info_error:
                        print(f"[EbaySearch] search_products_on_ebay failed with structured data: {info_error}")
                        continue
                    if ebay_info:
                        break
            if ebay_info and ebay_info.get('images'):
                for img_url in ebay_info['images'][:10]:
                    if img_url and img_url not in seen_photo_urls:
                        results['stock_photos'].append({
                            'url': img_url,
                            'thumbnail': img_url,
                            'title': 'eBay listing',
                            'source': 'ebay_api',
                        })
                        seen_photo_urls.add(img_url)

            collected_comps = []
            seen_ids = set()
            strategy_logs = []
            for entry in strategies:
                term = entry['term']
                fetched = []
                try:
                    print(f"[EbaySearch] Searching eBay comps for: {term}")
                    fetched = ebay_client.search_comps(query=term, limit=15)
                except Exception as search_error:
                    print(f"[EbaySearch] search_comps failed for '{term}': {search_error}")
                matched = []
                for comp in fetched or []:
                    item_id = str(comp.get('item_id') or comp.get('itemId') or comp.get('url') or '')
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    price = float(comp.get('price') or 0)
                    shipping = float(comp.get('shipping_cost') or 0)
                    total_price = float(comp.get('total_price') or (price + shipping))
                    enriched = {
                        'item_id': item_id,
                        'title': comp.get('title') or '',
                        'price': price,
                        'shipping_cost': shipping,
                        'total_price': total_price,
                        'currency': comp.get('currency') or 'USD',
                        'condition': comp.get('condition') or comp.get('condition_text') or '',
                        'condition_text': comp.get('condition_text'),
                        'seller_rating': comp.get('seller_rating'),
                        'location': comp.get('location'),
                        'url': comp.get('url'),
                        'image_url': comp.get('image_url'),
                        'sold_date': comp.get('sold_date'),
                        'note': comp.get('note'),
                        'strategy_term': term,
                        'strategy_source': entry['source'],
                        'strategy_reason': entry['reason'],
                    }
                    collected_comps.append(enriched)
                    matched.append(enriched)
                    if comp.get('image_url') and comp['image_url'] not in seen_photo_urls:
                        results['stock_photos'].append({
                            'url': comp['image_url'],
                            'thumbnail': comp['image_url'],
                            'title': comp.get('title', '')[:50],
                            'source': 'ebay_api',
                            'price': price,
                        })
                        seen_photo_urls.add(comp['image_url'])
                strategy_logs.append({
                    'term': term,
                    'source': entry['source'],
                    'reason': entry['reason'],
                    'found': len(matched),
                })

            totals = [c['total_price'] for c in collected_comps if c['total_price']]
            prices_only = [c['price'] for c in collected_comps if c['price']]
            if totals:
                totals_sorted = sorted(totals)
                price_info = {
                    'price': round(median(prices_only or totals_sorted), 2) if (prices_only or totals_sorted) else None,
                    'price_min': round(min(prices_only or totals_sorted), 2) if (prices_only or totals_sorted) else None,
                    'price_max': round(max(prices_only or totals_sorted), 2) if (prices_only or totals_sorted) else None,
                    'total_median': round(median(totals_sorted), 2),
                    'total_min': round(min(totals_sorted), 2),
                    'total_max': round(max(totals_sorted), 2),
                    'price_count': len(collected_comps),
                }
                results['price_info'] = price_info
            elif ebay_info and ebay_info.get('price'):
                results['price_info'] = {
                    'price': ebay_info.get('price'),
                    'price_min': ebay_info.get('price_min'),
                    'price_max': ebay_info.get('price_max'),
                    'price_count': ebay_info.get('price_count', 0),
                }

            results['comps'] = collected_comps
            results['strategies'] = strategy_logs
            if collected_comps:
                results['used_query'] = collected_comps[0]['strategy_term']

            # Augment with GPT photo queries if we still need imagery
            photo_queries = []
            for struct in analysis_structs:
                queries = struct.get('photo_queries') or []
                for q in queries:
                    if q:
                        photo_queries.append(str(q))
            dedup_queries = []
            seen_q = set()
            for q in photo_queries:
                cleaned = q.strip()
                if not cleaned:
                    continue
                sig = cleaned.lower()
                if sig in seen_q:
                    continue
                seen_q.add(sig)
                dedup_queries.append(cleaned)
            if dedup_queries and len(results['stock_photos']) < 12:
                try:
                    from photos.views import search_stock_photos
                    for q in dedup_queries[:3]:
                        try:
                            print(f"[EbaySearch] Searching stock photos via GPT query: {q}")
                            stock_candidates = search_stock_photos(q, None)
                            if isinstance(stock_candidates, dict):
                                stock_candidates = stock_candidates.get('images', [])
                            for photo in stock_candidates[:6]:
                                photo_url = photo.get('url') if isinstance(photo, dict) else photo
                                if photo_url and photo_url not in seen_photo_urls:
                                    results['stock_photos'].append({
                                        'url': photo_url,
                                        'thumbnail': photo_url,
                                        'title': q[:60],
                                        'source': 'gpt_photo_query',
                                    })
                                    seen_photo_urls.add(photo_url)
                                if len(results['stock_photos']) >= 18:
                                    break
                            if len(results['stock_photos']) >= 18:
                                break
                        except Exception as photo_err:
                            print(f"[EbaySearch] stock photo lookup failed for '{q}': {photo_err}")
                except Exception as photo_module_err:
                    print(f"[EbaySearch] stock photo module unavailable: {photo_module_err}")

            print(f"[EbaySearch] Found {len(collected_comps)} comps, {len(results['stock_photos'])} photos")

            if hasattr(candidate, 'analysis_data'):
                snapshot = analysis_data if isinstance(analysis_data, dict) else {}
                snapshot['ebay_comps_latest'] = {
                    'saved_at': timezone.now().isoformat(),
                    'strategies': strategy_logs,
                    'items': collected_comps,
                    'price_info': results['price_info'],
                }
                snapshot['ebay_stock_photos_latest'] = {
                    'saved_at': timezone.now().isoformat(),
                    'queries': dedup_queries,
                    'items': results['stock_photos'],
                }
                candidate.analysis_data = snapshot
                candidate.save(update_fields=['analysis_data', 'updated_at'])

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Exception in eBay search: {e}\n{traceback.format_exc()}")
            print(f"[EbaySearch] Exception: {e}")
            return Response({
                'error': str(e),
                'comps': [],
                'stock_photos': [],
                'price_info': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(results, status=status.HTTP_200_OK)


class GPTAnalysisView(APIView):
    """
    Run comprehensive GPT analysis for product listing.
    Extracts all data needed for eBay listing.
    
    POST /api/ebay/analyze/
    Body: {
        "candidate_id": 123,
        "provider": "openai" | "google" | "both"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        candidate_id = request.data.get('candidate_id')
        provider = request.data.get('provider', 'both')
        
        if not candidate_id:
            return Response(
                {'error': 'candidate_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        candidate = get_object_or_404(EbayCandidate, id=candidate_id)
        photo_batch = candidate.photo_batch
        
        if not photo_batch:
            return Response(
                {'error': 'No photo batch found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get photo URLs
        photos = photo_batch.photos.all()[:10]  # Up to 10 photos
        photo_urls = []
        barcodes = []
        gg_labels = []
        
        for photo in photos:
            if photo.image:
                request_host = request.get_host() if hasattr(request, 'get_host') else 'pochtoy.us'
                photo_url = f"https://{request_host}{photo.image.url}"
                photo_urls.append(photo_url)
            
            # Collect barcodes and GG labels
            for barcode in photo.barcodes.all():
                if barcode.data not in barcodes:
                    barcodes.append(barcode.data)
                # Check for GG labels
                if 'GG' in barcode.data.upper() or barcode.data.startswith('Q'):
                    gg_labels.append(barcode.data)
        
        if not photo_urls:
            return Response(
                {'error': 'No photos found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {}
        
        # OpenAI analysis
        if provider in ['openai', 'both']:
            try:
                import os
                import logging
                logger = logging.getLogger(__name__)
                
                # Check API key
                api_key = os.getenv('OPENAI_API_KEY')
                print(f"[GPTAnalysis] OpenAI API key check: {'Found' if api_key else 'NOT FOUND'} (length: {len(api_key) if api_key else 0})")
                logger.info(f"OpenAI API key check: {'Found' if api_key else 'NOT FOUND'} (length: {len(api_key) if api_key else 0})")
                
                from photos.ai_helpers import generate_product_summary
                print(f"[GPTAnalysis] Calling generate_product_summary with {len(photo_urls)} photo URLs, {len(barcodes) if barcodes else 0} barcodes")
                print(f"[GPTAnalysis] Photo URLs: {photo_urls[:2]}")
                logger.info(f"Calling generate_product_summary with {len(photo_urls)} photo URLs, {len(barcodes) if barcodes else 0} barcodes")
                
                openai_summary = generate_product_summary(
                    photo_urls=photo_urls,
                    barcodes=barcodes[:5] if barcodes else None,
                    gg_labels=gg_labels[:5] if gg_labels else None
                )
                
                print(f"[GPTAnalysis] generate_product_summary returned: {type(openai_summary)}, length: {len(openai_summary) if openai_summary else 0}")
                if openai_summary:
                    print(f"[GPTAnalysis] Summary preview: {openai_summary[:200]}")
                logger.info(f"generate_product_summary returned: {type(openai_summary)}, length: {len(openai_summary) if openai_summary else 0}")
                
                if not openai_summary:
                    error_msg = 'No summary generated'
                    if not api_key:
                        error_msg += ' - OpenAI API key not found in environment'
                    elif not photo_urls:
                        error_msg += ' - No photo URLs provided'
                    else:
                        # Check if it's an API key error by looking at logs
                        error_msg += ' - Possible issues: invalid/expired API key, API quota exceeded, or photo URLs not accessible. Check server logs for details.'
                    
                    results['openai'] = {
                        'success': False,
                        'error': error_msg
                    }
                else:
                    # Parse structured data from summary
                    structured_data = self._parse_summary_to_structured(openai_summary, barcodes, gg_labels)
                    
                    # Extract OpenAI photo search queries from summary
                    openai_photo_queries = []
                    openai_stock_photos = []
                    seen_photo_urls = set()  # Для предотвращения дубликатов
                    
                    try:
                        import re
                        print(f"[GPTAnalysis] Looking for photo queries in summary (length: {len(openai_summary) if openai_summary else 0})")
                        
                        # Look for photo search recommendations section - try multiple patterns
                        photo_queries_match = None
                        patterns = [
                            r'\*\*Рекомендации по стоковым фото.*?:\*\*\s*([\s\S]+?)(?:\*\*ВСЕ|$)',
                            r'\*\*Рекомендации по стоковым фото.*?:\*\*\s*([\s\S]+?)(?:\*\*|$)',
                            r'Рекомендации по стоковым фото.*?:\s*([\s\S]+?)(?:\*\*|$)',
                        ]
                        
                        for pattern in patterns:
                            photo_queries_match = re.search(pattern, openai_summary, re.IGNORECASE)
                            if photo_queries_match:
                                print(f"[GPTAnalysis] Found photo queries section with pattern: {pattern[:50]}")
                                break
                        
                        if not photo_queries_match:
                            print(f"[GPTAnalysis] Photo queries section not found. Summary preview: {openai_summary[:500] if openai_summary else 'None'}")
                            # Try to extract queries from any list-like format
                            if openai_summary:
                                # Look for quoted strings that look like search queries
                                quoted_queries = re.findall(r'["\']([^"\']{20,}?)["\']', openai_summary)
                                if quoted_queries:
                                    openai_photo_queries = [q for q in quoted_queries if len(q) > 20][:5]
                                    print(f"[GPTAnalysis] Extracted {len(openai_photo_queries)} queries from quoted strings")
                        else:
                            queries_text = photo_queries_match.group(1).strip()
                            print(f"[GPTAnalysis] Extracted queries text (length: {len(queries_text)})")
                            # Extract each line as a query
                            for line in queries_text.split('\n'):
                                line = line.strip()
                                if line and not line.startswith('**') and len(line) > 10:
                                    # Remove bullet points and clean
                                    line = re.sub(r'^[-•*]\s*', '', line)
                                    # Remove quotes if present
                                    line = re.sub(r'^["\']|["\']$', '', line)
                                    if line and len(line) > 10:
                                        openai_photo_queries.append(line)
                        
                        print(f"[GPTAnalysis] Extracted {len(openai_photo_queries)} photo queries: {openai_photo_queries}")
                        
                        # Поиск стоковых фото только через Google/DuckDuckGo (eBay поиск вынесен в отдельный endpoint)
                        if openai_photo_queries:
                            from photos.views import search_stock_photos
                            print(f"[GPTAnalysis] Searching Google/DuckDuckGo for {len(openai_photo_queries)} queries")
                            for query in openai_photo_queries[:3]:  # Use first 3 queries
                                try:
                                    print(f"[GPTAnalysis] Searching Google/DuckDuckGo for query: '{query}'")
                                    result = search_stock_photos(query, None)
                                    print(f"[GPTAnalysis] search_stock_photos returned: {type(result)}, length: {len(result) if isinstance(result, (list, dict)) else 'N/A'}")
                                    if result:
                                        if isinstance(result, list):
                                            print(f"[GPTAnalysis] Result is list with {len(result)} items")
                                            for photo in result[:4]:  # 4 photos per query
                                                photo_url = photo.get('url') if isinstance(photo, dict) else photo
                                                if photo_url and photo_url not in seen_photo_urls:
                                                    openai_stock_photos.append({
                                                        'url': photo_url,
                                                        'thumbnail': photo_url,
                                                        'title': query,
                                                        'source': photo.get('source', 'openai_search') if isinstance(photo, dict) else 'openai_search'
                                                    })
                                                    seen_photo_urls.add(photo_url)
                                                    print(f"[GPTAnalysis] Added photo: {photo_url[:50]}")
                                                    if len(openai_stock_photos) >= 12:
                                                        break
                                        elif isinstance(result, dict) and 'images' in result:
                                            print(f"[GPTAnalysis] Result is dict with {len(result['images'])} images")
                                            for photo in result['images'][:4]:
                                                photo_url = photo.get('url') if isinstance(photo, dict) else photo
                                                if photo_url and photo_url not in seen_photo_urls:
                                                    openai_stock_photos.append({
                                                        'url': photo_url,
                                                        'thumbnail': photo_url,
                                                        'title': query,
                                                        'source': 'openai_search'
                                                    })
                                                    seen_photo_urls.add(photo_url)
                                                    print(f"[GPTAnalysis] Added photo: {photo_url[:50]}")
                                                    if len(openai_stock_photos) >= 12:
                                                        break
                                    else:
                                        print(f"[GPTAnalysis] No results for query: '{query}'")
                                    if len(openai_stock_photos) >= 12:
                                        break
                                except Exception as e:
                                    import traceback
                                    print(f"[GPTAnalysis] Error searching photos for query '{query}': {e}")
                                    traceback.print_exc()
                        else:
                            print(f"[GPTAnalysis] No photo queries extracted from summary")
                        
                        # Используем только фото из Google/DuckDuckGo (eBay поиск вынесен в отдельный endpoint)
                        all_stock_photos = openai_stock_photos
                        print(f"[GPTAnalysis] Total found {len(all_stock_photos)} photos from Google/DuckDuckGo")
                    except Exception as e:
                        import traceback
                        print(f"[GPTAnalysis] Error extracting OpenAI photo queries: {e}")
                        traceback.print_exc()
                        all_stock_photos = []
                    
                    self._store_structured_data(candidate, structured_data, provider='openai')

                    structured_data.setdefault('photo_queries', openai_photo_queries[:5] if openai_photo_queries else [])
                    structured_data.setdefault('price_range_hint', structured_data.get('price_range'))
                    results['openai'] = {
                        'success': True,
                        'summary': openai_summary,
                        'data': structured_data,
                        'stock_photos': all_stock_photos,
                        'photo_queries': openai_photo_queries[:5] if openai_photo_queries else []
                    }
            except ValueError as e:
                # Handle specific API errors + add base64 fallback when OpenAI can't download URLs
                error_msg = str(e)
                # Fallback: if OpenAI failed to download images (http/http->https, TLS, robots etc.)
                try_fallback = ('Error while downloading' in error_msg) or ('http://' in error_msg) or ('https://' in error_msg and 'download' in error_msg.lower())
                if try_fallback:
                    try:
                        import base64
                        photo_data_list = []
                        for p in photos[:5]:
                            if not getattr(p, 'image', None):
                                continue
                            try:
                                with p.image.open('rb') as f:
                                    b64 = base64.b64encode(f.read()).decode('ascii')
                                photo_data_list.append({'base64': b64, 'mime_type': 'image/jpeg'})
                            except Exception:
                                continue
                        if photo_data_list:
                            openai_summary = generate_product_summary(
                                photo_data_list=photo_data_list,
                                barcodes=barcodes[:5] if barcodes else None,
                                gg_labels=gg_labels[:5] if gg_labels else None
                            )
                            if openai_summary:
                                structured_data = self._parse_summary_to_structured(openai_summary, barcodes, gg_labels)
                                self._store_structured_data(candidate, structured_data, provider='openai')
                                results['openai'] = {
                                    'success': True,
                                    'summary': openai_summary,
                                    'data': structured_data,
                                    'stock_photos': [],
                                    'photo_queries': []
                                }
                                # Fallback succeeded; stop further error handling
                                error_msg = ''
                    except Exception:
                        pass
                if error_msg:
                    if 'API key error' in error_msg:
                        error_msg = 'Invalid or expired OpenAI API key. Please update OPENAI_API_KEY in .env file.'
                    elif 'rate limit' in error_msg.lower():
                        error_msg = 'OpenAI API rate limit exceeded. Please try again later.'
                    results['openai'] = {
                        'success': False,
                        'error': error_msg
                    }
            except Exception as e:
                import traceback
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Exception in OpenAI analysis: {e}\n{traceback.format_exc()}")
                print(f"[GPTAnalysis] Exception: {e}")
                results['openai'] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Google analysis
        if provider in ['google', 'both']:
            try:
                from photos.ai_helpers import generate_product_description
                google_description = None
                if barcodes:
                    google_description = generate_product_description(
                        barcode=barcodes[0],
                        photos_text=f"Product photos: {len(photo_urls)} images"
                    )
                
                google_data = self._parse_google_to_structured(google_description, barcodes)
                self._store_structured_data(candidate, google_data, provider='google')

                results['google'] = {
                    'success': True,
                    'description': google_description or 'Google analysis not available',
                    'data': google_data
                }
            except Exception as e:
                results['google'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return Response(results, status=status.HTTP_200_OK)
    
    def _store_structured_data(self, candidate: EbayCandidate, structured: dict, provider: str) -> None:
        """Persist structured analysis snapshot and backfill candidate fields."""
        if not isinstance(structured, dict):
            return
        
        # Some older dev DBs may not have analysis_data field; handle gracefully
        has_analysis_field = any(getattr(f, 'name', None) == 'analysis_data' for f in candidate._meta.get_fields())
        raw_analysis = getattr(candidate, 'analysis_data', {}) if has_analysis_field else {}
        analysis_snapshot = raw_analysis if isinstance(raw_analysis, dict) else {}
        snapshot_copy = structured.copy()
        snapshot_copy['provider'] = provider
        snapshot_copy['saved_at'] = timezone.now().isoformat()
        analysis_snapshot[f'{provider}_latest'] = snapshot_copy
        
        # Merge keywords & barcodes across analyses
        def _merge_list(key: str, values: list):
            if not values:
                return
            existing = analysis_snapshot.get(key, [])
            if not isinstance(existing, list):
                existing = []
            seen = {str(item).lower() for item in existing}
            for item in values:
                normalized = str(item).lower()
                if normalized not in seen:
                    existing.append(item)
                    seen.add(normalized)
            analysis_snapshot[key] = existing
        
        _merge_list('keywords', structured.get('keywords'))
        _merge_list('barcodes', structured.get('barcodes'))
        _merge_list('search_queries', [structured.get('search_query')])
        _merge_list('brands', [structured.get('brand')])
        _merge_list('models', [structured.get('model')])
        _merge_list('photo_queries', structured.get('photo_queries'))
        _merge_list('price_hints', [structured.get('price')])
        if structured.get('price_range') or structured.get('price_range_hint'):
            _merge_list('price_ranges', [structured.get('price_range') or structured.get('price_range_hint')])
        
        analysis_snapshot['last_provider'] = provider
        analysis_snapshot['last_updated'] = timezone.now().isoformat()
        if has_analysis_field:
            candidate.analysis_data = analysis_snapshot
            update_fields = {'analysis_data', 'updated_at'}
        else:
            update_fields = {'updated_at'}
        
        # Only backfill candidate fields if empty (avoid overwriting manual edits)
        title = structured.get('title')
        if title and not candidate.title:
            candidate.title = title[:80]
            update_fields.add('title')
        
        description = structured.get('description')
        if description and not candidate.description_md:
            candidate.description_md = description[:10000]
            update_fields.add('description_md')
        
        category_id = structured.get('category_id')
        if category_id and not candidate.category_id:
            candidate.category_id = str(category_id)
            update_fields.add('category_id')
        
        condition = structured.get('condition')
        if condition and not candidate.condition:
            candidate.condition = condition
            update_fields.add('condition')
        
        price = structured.get('price')
        if price is not None and candidate.price_suggested is None:
            try:
                candidate.price_suggested = Decimal(str(price))
                update_fields.add('price_suggested')
            except (InvalidOperation, TypeError, ValueError):
                pass
        
        specifics = structured.get('specifics')
        if isinstance(specifics, dict) and specifics:
            merged = candidate.specifics.copy() if isinstance(candidate.specifics, dict) else {}
            merged.update(specifics)
            candidate.specifics = merged
            update_fields.add('specifics')
        
        if update_fields:
            candidate.save(update_fields=list(update_fields))
    
    def _parse_summary_to_structured(self, summary: str, barcodes: list, gg_labels: list = None) -> dict:
        """Parse GPT summary into structured eBay listing data."""
        import re
        
        if not summary:
            summary = ''
        
        data = {
            'title': '',
            'description': summary,
            'brand': '',
            'model': '',
            'category_id': '260324',  # Default to watches
            'condition': 'NEW',
            'specifics': {},
            'technical_specs': {},
            'keywords': [],
            'barcodes': barcodes or [],
            'gg_labels': gg_labels or [],
        }
        
        # Extract "Что это за товар" - это будет title
        title_patterns = [
            r'\*\*Что это за товар.*?:\*\*\s*(.+?)(?:\n|$)',
            r'\*\*Что это за товар \(точное название\):\*\*\s*(.+?)(?:\n|$)',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, summary, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Clean up markdown
                title = re.sub(r'\*\*', '', title)
                if len(title) <= 80:
                    data['title'] = title
                else:
                    data['title'] = title[:77] + '...'
                break
        
        # Extract brand and model (improved patterns)
        brand_model_patterns = [
            r'\*\*Бренд и ТОЧНАЯ модель:\*\*\s*(.+?)(?:\n|$)',
            r'\*\*Бренд и модель:\*\*\s*(.+?)(?:\n|$)',
            r'Brand.*?Model.*?:\s*(.+?)(?:\n|$)',
        ]
        for pattern in brand_model_patterns:
            match = re.search(pattern, summary, re.IGNORECASE | re.DOTALL)
            if match:
                brand_model = match.group(1).strip()
                # Try to split brand and model
                # Common patterns: "Casio G-SHOCK GM-2110D-2AER" or "G-SHOCK GM-2110D-2AER"
                parts = brand_model.split()
                if len(parts) >= 2:
                    # Find model (usually contains dash and numbers/letters)
                    model_match = re.search(r'([A-Z]+-?\d+[A-Z]?-\d+[A-Z]+)', brand_model)
                    if model_match:
                        data['model'] = model_match.group(1)
                        # Brand is everything before model
                        brand_part = brand_model[:model_match.start()].strip()
                        if brand_part:
                            data['brand'] = brand_part
                    else:
                        # No clear model pattern, use first part as brand
                        data['brand'] = parts[0]
                        if len(parts) > 1:
                            data['model'] = ' '.join(parts[1:])
                else:
                    data['brand'] = brand_model
                break
        
        # Extract technical specs
        tech_specs_patterns = [
            r'\*\*Технические характеристики.*?:\*\*\s*(.+?)(?:\*\*|$)',
        ]
        for pattern in tech_specs_patterns:
            match = re.search(pattern, summary, re.IGNORECASE | re.DOTALL)
            if match:
                tech_specs = match.group(1).strip()
                # Parse common watch specs
                if 'диаметр' in tech_specs.lower() or 'diameter' in tech_specs.lower():
                    diameter_match = re.search(r'(\d+\.?\d*)\s*мм', tech_specs, re.IGNORECASE)
                    if diameter_match:
                        data['technical_specs']['case_diameter'] = diameter_match.group(1) + ' mm'
                if 'толщина' in tech_specs.lower() or 'thickness' in tech_specs.lower():
                    thickness_match = re.search(r'(\d+\.?\d*)\s*мм', tech_specs, re.IGNORECASE)
                    if thickness_match:
                        data['technical_specs']['case_thickness'] = thickness_match.group(1) + ' mm'
                if 'водонепроницаемость' in tech_specs.lower() or 'water' in tech_specs.lower():
                    water_match = re.search(r'(\d+)\s*(?:м|m|bar|бар)', tech_specs, re.IGNORECASE)
                    if water_match:
                        data['technical_specs']['water_resistance'] = water_match.group(1) + 'm'
                data['technical_specs']['full_specs'] = tech_specs[:500]  # Limit length
                break
        
        # Extract condition
        condition_patterns = [
            r'\*\*Состояние товара:\*\*\s*(.+?)(?:\n|$)',
        ]
        for pattern in condition_patterns:
            match = re.search(pattern, summary, re.IGNORECASE)
            if match:
                condition = match.group(1).strip().lower()
                if 'new' in condition or 'новый' in condition:
                    data['condition'] = 'NEW'
                elif 'used' in condition or 'б/у' in condition:
                    data['condition'] = 'USED_GOOD'
                break
        
        # Extract price
        price_patterns = [
            r'\*\*Рекомендуемая розничная цена.*?:\*\*\s*(\d+\.?\d*)',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, summary, re.IGNORECASE)
            if match:
                data['price'] = float(match.group(1))
                break
        
        # Try to detect category from summary
        summary_lower = summary.lower()
        if any(word in summary_lower for word in ['watch', 'часы', 'wristwatch', 'g-shock', 'casio']):
            data['category_id'] = '260324'
        elif any(word in summary_lower for word in ['shoe', 'обувь', 'sneaker']):
            data['category_id'] = '93427'
        elif any(word in summary_lower for word in ['perfume', 'парфюм', 'cologne']):
            data['category_id'] = '31518'
        
        # Add barcodes to specifics if found
        if barcodes:
            data['specifics']['UPC'] = barcodes[0]
        
        # Build search keywords & query
        keyword_candidates = []
        for field in [data.get('brand'), data.get('model')]:
            if field:
                keyword_candidates.extend(field.replace('/', ' ').split())
        if data.get('title'):
            keyword_candidates.extend([word for word in data['title'].split() if len(word) > 2])
        if gg_labels:
            keyword_candidates.extend(gg_labels)
        if barcodes:
            keyword_candidates.extend(barcodes)
        
        seen = set()
        keywords = []
        for word in keyword_candidates:
            cleaned = word.strip().strip(',.;:')
            lowered = cleaned.lower()
            if cleaned and lowered not in seen:
                seen.add(lowered)
                keywords.append(cleaned)
        data['keywords'] = keywords
        data['search_query'] = ' '.join(keywords[:8]) if keywords else ''
        
        # If we have brand and model, try to search eBay for more info
        if data.get('brand') and data.get('model'):
            try:
                from photos.ai_helpers import search_products_on_ebay
                ebay_info = search_products_on_ebay(
                    brand=data['brand'],
                    model=data['model'],
                    barcode=barcodes[0] if barcodes else None
                )
                if ebay_info:
                    if ebay_info.get('price') and not data.get('price'):
                        data['price'] = ebay_info['price']
                    if ebay_info.get('price_min') and ebay_info.get('price_max'):
                        data['price_range'] = f"${ebay_info['price_min']:.2f} - ${ebay_info['price_max']:.2f}"
            except Exception as e:
                print(f"[Parse] eBay search error: {e}")
        
        data['photo_queries'] = data.get('photo_queries') or []
        return data
    
    def _parse_google_to_structured(self, description: str, barcodes: list) -> dict:
        """Parse Google description into structured data."""
        if not description:
            description = ''
        title = description.split('.')[0][:80] if description else ''
        keywords = []
        if title:
            keywords.extend([word for word in title.split() if len(word) > 2])
        if barcodes:
            keywords.extend(barcodes)
        seen = set()
        deduped_keywords = []
        for word in keywords:
            clean = word.strip().strip(',.;:')
            lowered = clean.lower()
            if clean and lowered not in seen:
                seen.add(lowered)
                deduped_keywords.append(clean)
        return {
            'title': description.split('.')[0][:80] if description else '',
            'description': description or '',
            'category_id': '260324',
            'condition': 'USED_GOOD',
            'specifics': {'UPC': barcodes[0]} if barcodes else {},
            'keywords': deduped_keywords,
            'search_query': ' '.join(deduped_keywords[:8]) if deduped_keywords else '',
            'barcodes': barcodes or [],
            'photo_queries': [],
            'price': None,
            'price_range': None,
        }


@method_decorator(csrf_exempt, name='dispatch')
class GPTPreviewView(APIView):
    """
    Generate GPT previews for product listing (legacy endpoint).
    
    POST /api/ebay/gpt-preview/
    Body: {
        "candidate_id": 123,
        "provider": "openai" | "google" | "both"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Redirect to new analyze endpoint
        view = GPTAnalysisView()
        return view.post(request)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def ebay_marketplace_deletion_webhook(request):
    """
    eBay Marketplace Account Deletion notification endpoint.
    
    This endpoint receives notifications from eBay when a marketplace account
    is deleted or closed. Required for API compliance.
    
    GET: Verification challenge (eBay sends verification token)
    POST: Actual notification about account deletion
    """
    import os
    
    # GET request - verification challenge
    if request.method == 'GET':
        verification_token = request.GET.get('challenge_code')
        expected_token = os.getenv('EBAY_VERIFICATION_TOKEN', '')
        
        if verification_token and expected_token and verification_token == expected_token:
            print(f"[eBay Webhook] Verification successful: {verification_token[:10]}...")
            return JsonResponse({'challengeResponse': verification_token})
        else:
            print(f"[eBay Webhook] Verification failed or token not set")
            return JsonResponse({'error': 'Invalid verification token'}, status=400)
    
    # POST request - actual notification
    try:
        data = json.loads(request.body) if request.body else {}
        print(f"[eBay Webhook] Received marketplace deletion notification: {data}")
        
        # Log the notification (you can extend this to actually handle the deletion)
        # For now, we just acknowledge receipt
        
        return JsonResponse({'status': 'received'}, status=200)
    except Exception as e:
        print(f"[eBay Webhook] Error processing notification: {e}")
        return JsonResponse({'error': str(e)}, status=500)
