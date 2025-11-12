"""
eBay marketplace DRF views.
"""
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
class GPTPreviewView(APIView):
    """
    Generate GPT previews for product listing.
    
    POST /api/ebay/gpt-preview/
    Body: {
        "candidate_id": 123,
        "provider": "openai" | "google" | "both"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        candidate_id = request.data.get('candidate_id')
        provider = request.data.get('provider', 'both')  # 'openai', 'google', 'both'
        
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
        photos = photo_batch.photos.all()[:5]  # Limit to 5 photos
        photo_urls = []
        for photo in photos:
            if photo.image:
                request_scheme = request.scheme if hasattr(request, 'scheme') else 'https'
                request_host = request.get_host() if hasattr(request, 'get_host') else 'pochtoy.us'
                photo_url = f"{request_scheme}://{request_host}{photo.image.url}"
                photo_urls.append(photo_url)
        
        if not photo_urls:
            return Response(
                {'error': 'No photos found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get barcodes
        barcodes = []
        for photo in photos:
            for barcode in photo.barcodes.all():
                barcodes.append(barcode.data)
        
        results = {}
        
        # OpenAI preview
        if provider in ['openai', 'both']:
            try:
                from photos.ai_helpers import generate_product_summary
                openai_preview = generate_product_summary(
                    photo_urls=photo_urls,
                    barcodes=barcodes[:3] if barcodes else None
                )
                results['openai'] = {
                    'success': True,
                    'preview': openai_preview
                }
            except Exception as e:
                results['openai'] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Google preview (using Google Product Search or similar)
        if provider in ['google', 'both']:
            try:
                # For now, use a simple description generation
                # In production, this would use Google Product Search API
                from photos.ai_helpers import generate_product_description
                google_preview = None
                if barcodes:
                    google_preview = generate_product_description(
                        barcode=barcodes[0],
                        photos_text=f"Product photos: {len(photo_urls)} images"
                    )
                results['google'] = {
                    'success': True,
                    'preview': google_preview or 'Google preview not available'
                }
            except Exception as e:
                results['google'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return Response(results, status=status.HTTP_200_OK)
