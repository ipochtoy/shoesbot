"""
eBay marketplace URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EbayCandidateViewSet,
    BulkCreateCandidatesView,
    TaxonomySuggestView,
    ItemSpecificsView,
    PricingCompsView,
    EbayTokenViewSet,
    ebay_candidate_edit,
    GPTPreviewView,
)

app_name = 'ebay'

# DRF Router
router = DefaultRouter()
router.register(r'candidates', EbayCandidateViewSet, basename='candidate')
router.register(r'tokens', EbayTokenViewSet, basename='token')

urlpatterns = [
    # Edit page (non-API)
    path('candidates/<int:candidate_id>/edit/', ebay_candidate_edit, name='candidate-edit'),
    
    # Bulk operations
    path('candidates/bulk-create/', BulkCreateCandidatesView.as_view(), name='bulk-create'),

    # Taxonomy & category endpoints
    path('taxonomy/suggest/', TaxonomySuggestView.as_view(), name='taxonomy-suggest'),
    path('specifics/', ItemSpecificsView.as_view(), name='item-specifics'),

    # Pricing endpoints
    path('pricing/comps/', PricingCompsView.as_view(), name='pricing-comps'),

    # GPT Preview endpoints
    path('gpt-preview/', GPTPreviewView.as_view(), name='gpt-preview'),

    # Include router URLs
    path('', include(router.urls)),
]
