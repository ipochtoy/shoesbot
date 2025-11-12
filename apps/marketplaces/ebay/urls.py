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
    ebay_candidate_analyze,
    ebay_candidate_edit,
    GPTPreviewView,
    GPTAnalysisView,
    EbaySearchView,
    ebay_marketplace_deletion_webhook,
)

app_name = 'ebay'

# DRF Router
router = DefaultRouter()
router.register(r'candidates', EbayCandidateViewSet, basename='candidate')
router.register(r'tokens', EbayTokenViewSet, basename='token')

urlpatterns = [
    # Analysis page (first step)
    path('candidates/<int:candidate_id>/analyze/', ebay_candidate_analyze, name='candidate-analyze'),
    # Edit page (second step)
    path('candidates/<int:candidate_id>/edit/', ebay_candidate_edit, name='candidate-edit'),
    
    # Bulk operations
    path('candidates/bulk-create/', BulkCreateCandidatesView.as_view(), name='bulk-create'),

    # Taxonomy & category endpoints
    path('taxonomy/suggest/', TaxonomySuggestView.as_view(), name='taxonomy-suggest'),
    path('specifics/', ItemSpecificsView.as_view(), name='item-specifics'),

    # Pricing endpoints
    path('pricing/comps/', PricingCompsView.as_view(), name='pricing-comps'),

    # GPT Analysis endpoints
    path('analyze/', GPTAnalysisView.as_view(), name='gpt-analyze'),
    path('gpt-preview/', GPTPreviewView.as_view(), name='gpt-preview'),
    
    # eBay Search endpoint (separate from analysis to avoid timeouts)
    path('search/', EbaySearchView.as_view(), name='ebay-search'),
    
    # eBay Marketplace Account Deletion webhook (for API compliance)
    path('webhook/marketplace-deletion/', ebay_marketplace_deletion_webhook, name='ebay-marketplace-deletion-webhook'),

    # Include router URLs
    path('', include(router.urls)),
]
