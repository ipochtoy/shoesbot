"""
eBay listing preparation pipeline.

Orchestrates the full preparation workflow:
1. Vision extraction from photos
2. Category suggestion
3. Fetch required specifics
4. Generate listing content
5. Find comparable listings
6. Calculate pricing
7. Finalize candidate data
"""
from typing import Dict, Any
from django.utils import timezone
from django.conf import settings

from ..models import EbayCandidate
from .client import EbayClient
from .gpt import GPTService
from .pricing import PricingService


def prepare_candidate(candidate_id: int) -> Dict[str, Any]:
    """
    Run full preparation pipeline on a candidate.

    Pipeline steps:
    1. Extract product data from photos (GPT Vision)
    2. Suggest eBay category
    3. Fetch required item specifics for category
    4. Generate listing content (title, description, bullets)
    5. Browse comparable listings
    6. Calculate pricing
    7. Prepare photos list
    8. Set business policies
    9. Validate and update status

    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict with status and candidate data
    """
    try:
        candidate = EbayCandidate.objects.select_related('photo_batch').get(id=candidate_id)
    except EbayCandidate.DoesNotExist:
        return {
            'success': False,
            'message': f'Candidate {candidate_id} not found'
        }

    candidate.add_log('info', 'Starting preparation pipeline')

    # Initialize services
    ebay_client = EbayClient()
    gpt_service = GPTService()
    pricing_service = PricingService()

    batch = candidate.photo_batch

    # Step 1: Extract data from photos using Vision AI
    candidate.add_log('info', 'Step 1: Extracting data from photos')

    # Get photo URLs
    photo_urls = [photo.image.url for photo in batch.photos.all() if photo.image]

    if not photo_urls:
        candidate.add_log('warning', 'No photos found in batch')
        photo_urls = []

    # Run vision extraction (stub for now)
    extracted = gpt_service.vision_extract(photo_urls)
    candidate.add_log('info', f'Vision extraction complete', extracted)

    # Step 2: Suggest category
    candidate.add_log('info', 'Step 2: Suggesting eBay category')

    # Build category search query
    category_query_parts = []

    # Use extracted brand/model or fallback to batch data
    brand = extracted.get('brand') if extracted.get('brand') != 'UNKNOWN' else batch.brand
    model = extracted.get('model') if extracted.get('model') != 'UNKNOWN' else ''

    if brand:
        category_query_parts.append(brand)
    if model:
        category_query_parts.append(model)
    if batch.category:
        category_query_parts.append(batch.category)
    if batch.title:
        category_query_parts.append(batch.title)

    category_query = ' '.join(category_query_parts).strip() or 'general product'

    # Get category suggestions
    categories = ebay_client.search_categories(category_query)

    if categories:
        # Use first suggestion
        suggested_category = categories[0]
        candidate.category_id = suggested_category['category_id']
        candidate.add_log('info', f'Category suggested: {suggested_category["category_name"]} ({suggested_category["category_id"]})')
    else:
        candidate.add_log('warning', 'No category suggestions found')
        # Use default category
        candidate.category_id = '99999'  # Miscellaneous

    # Step 3: Fetch required specifics
    candidate.add_log('info', 'Step 3: Fetching required item specifics')

    required_specifics = ebay_client.get_required_specifics(candidate.category_id)
    candidate.add_log('info', f'Found {len(required_specifics)} item specifics for category')

    # Step 4: Generate listing content
    candidate.add_log('info', 'Step 4: Generating listing content')

    listing_data = gpt_service.write_listing(
        extracted_data=extracted,
        category_name=categories[0]['category_name'] if categories else 'General',
    )

    # Update candidate with generated content
    candidate.title = listing_data['title']
    candidate.description_md = listing_data['description_md']
    candidate.condition = listing_data['condition']

    # Merge specifics
    candidate.specifics = listing_data.get('specifics', {})

    candidate.add_log('info', f'Listing content generated: "{candidate.title}"')

    # Step 5: Browse comparable listings
    candidate.add_log('info', 'Step 5: Finding comparable listings')

    pricing_result = pricing_service.calculate_price_for_candidate(candidate)

    if pricing_result.get('comps'):
        candidate.add_log(
            'info',
            f'Found {len(pricing_result["comps"])} comps, median: ${pricing_result.get("median", 0)}'
        )
    else:
        candidate.add_log('warning', 'No comparable listings found')

    # Step 6: Prepare photos list
    candidate.add_log('info', 'Step 6: Preparing photos')

    # Order photos: main first, then others
    photos_list = []
    main_photo = batch.photos.filter(is_main=True).first()

    if main_photo and main_photo.image:
        photos_list.append(main_photo.image.url)

    # Add other photos
    for photo in batch.photos.exclude(id=main_photo.id if main_photo else None).order_by('order', 'id'):
        if photo.image:
            # Convert to full URL if needed
            url = photo.image.url
            if url.startswith('/'):
                # Add domain
                domain = getattr(settings, 'PHOTO_HOST_DOMAIN', 'https://pochtoy.us')
                url = f'{domain}{url}'
            photos_list.append(url)

    candidate.photos = photos_list[:12]  # eBay max 12 photos
    candidate.add_log('info', f'Prepared {len(candidate.photos)} photos')

    # Step 7: Set business policies
    candidate.add_log('info', 'Step 7: Setting business policies')

    policies = ebay_client.get_business_policies()
    candidate.policies = policies
    candidate.add_log('info', 'Business policies set')

    # Step 8: Validate and finalize
    candidate.add_log('info', 'Step 8: Validating candidate')

    missing = candidate.missing_required_fields

    if missing:
        candidate.status = 'draft'
        candidate.add_log('warning', f'Missing required fields: {", ".join(missing)}')
        message = f'Preparation incomplete. Missing: {", ".join(missing)}'
    else:
        candidate.status = 'ready'
        candidate.add_log('info', 'All required fields filled. Candidate ready for publishing.')
        message = 'Preparation complete. Candidate ready for publishing.'

    # Update timestamps
    candidate.prepared_at = timezone.now()
    candidate.save()

    return {
        'success': True,
        'status': candidate.status,
        'message': message,
        'missing_fields': missing,
        'candidate': candidate,
    }


def publish_candidate(candidate_id: int) -> Dict[str, Any]:
    """
    Publish candidate to eBay.

    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    try:
        candidate = EbayCandidate.objects.get(id=candidate_id)
    except EbayCandidate.DoesNotExist:
        return {
            'success': False,
            'message': f'Candidate {candidate_id} not found'
        }

    # Validate
    if candidate.status == 'listed':
        return {
            'success': False,
            'message': 'Candidate is already listed'
        }

    missing = candidate.missing_required_fields
    if missing:
        candidate.add_log('error', f'Cannot publish: missing required fields - {", ".join(missing)}')
        return {
            'success': False,
            'message': f'Missing required fields: {", ".join(missing)}'
        }

    candidate.add_log('info', 'Publishing to eBay')

    # Publish via eBay client
    ebay_client = EbayClient()

    try:
        result = ebay_client.create_or_update_listing(candidate)

        if result.get('success'):
            candidate.ebay_item_id = result['item_id']
            candidate.status = 'listed'
            candidate.listed_at = timezone.now()
            candidate.save()

            candidate.add_log('info', f'Published successfully. Item ID: {result["item_id"]}', result)

            return {
                'success': True,
                'message': 'Published to eBay successfully',
                'ebay_item_id': result['item_id'],
                'listing_url': result.get('listing_url'),
                'candidate': candidate,
            }
        else:
            candidate.status = 'error'
            candidate.save()
            candidate.add_log('error', 'Publishing failed', result)

            return {
                'success': False,
                'message': 'eBay API error',
                'candidate': candidate,
            }

    except Exception as e:
        candidate.status = 'error'
        candidate.save()
        candidate.add_log('error', f'Exception during publishing: {str(e)}')

        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'candidate': candidate,
        }


def end_candidate(candidate_id: int) -> Dict[str, Any]:
    """
    End eBay listing.

    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    try:
        candidate = EbayCandidate.objects.get(id=candidate_id)
    except EbayCandidate.DoesNotExist:
        return {
            'success': False,
            'message': f'Candidate {candidate_id} not found'
        }

    if candidate.status != 'listed':
        return {
            'success': False,
            'message': 'Candidate is not currently listed'
        }

    if not candidate.ebay_item_id:
        return {
            'success': False,
            'message': 'No eBay item ID found'
        }

    candidate.add_log('info', f'Ending listing {candidate.ebay_item_id}')

    # End via eBay client
    ebay_client = EbayClient()

    try:
        result = ebay_client.end_listing(candidate.ebay_item_id)

        if result.get('success'):
            candidate.status = 'ended'
            candidate.ended_at = timezone.now()
            candidate.save()

            candidate.add_log('info', 'Listing ended successfully', result)

            return {
                'success': True,
                'message': 'Listing ended successfully',
                'candidate': candidate,
            }
        else:
            candidate.add_log('error', 'Failed to end listing', result)
            return {
                'success': False,
                'message': 'Failed to end listing',
                'candidate': candidate,
            }

    except Exception as e:
        candidate.add_log('error', f'Exception while ending listing: {str(e)}')
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'candidate': candidate,
        }


def reprice_candidate(candidate_id: int) -> Dict[str, Any]:
    """
    Reprice candidate based on current market.

    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    try:
        candidate = EbayCandidate.objects.get(id=candidate_id)
    except EbayCandidate.DoesNotExist:
        return {
            'success': False,
            'message': f'Candidate {candidate_id} not found'
        }

    candidate.add_log('info', 'Starting repricing')

    pricing_service = PricingService()
    result = pricing_service.reprice_candidate(candidate)

    return {
        **result,
        'candidate': candidate,
    }
