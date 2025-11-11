"""
Celery tasks for eBay marketplace operations.

Tasks are organized into queues:
- ebay_io: eBay API calls (create, update, end listings)
- pricing: Pricing calculations and comps fetching
- gpt: GPT/AI operations (vision, content generation)
"""
from celery import shared_task
from typing import List

from .services import pipeline as pipeline_service


@shared_task(queue='gpt', name='ebay.prepare_candidate')
def prepare_candidate(candidate_id: int) -> dict:
    """
    Run preparation pipeline on a candidate (GPT Vision + content generation).

    Queue: gpt
    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    return pipeline_service.prepare_candidate(candidate_id)


@shared_task(queue='ebay_io', name='ebay.publish_candidate')
def publish_candidate(candidate_id: int) -> dict:
    """
    Publish candidate to eBay.

    Queue: ebay_io
    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    return pipeline_service.publish_candidate(candidate_id)


@shared_task(queue='ebay_io', name='ebay.end_candidate')
def end_candidate(candidate_id: int) -> dict:
    """
    End eBay listing.

    Queue: ebay_io
    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    return pipeline_service.end_candidate(candidate_id)


@shared_task(queue='pricing', name='ebay.reprice_candidate')
def reprice_candidate(candidate_id: int) -> dict:
    """
    Reprice candidate based on current market.

    Queue: pricing
    Args:
        candidate_id: EbayCandidate ID

    Returns:
        Result dict
    """
    return pipeline_service.reprice_candidate(candidate_id)


@shared_task(queue='gpt', name='ebay.bulk_prepare')
def bulk_prepare(candidate_ids: List[int]) -> dict:
    """
    Prepare multiple candidates in bulk.

    Queue: gpt
    Args:
        candidate_ids: List of EbayCandidate IDs

    Returns:
        Summary dict
    """
    results = {
        'total': len(candidate_ids),
        'success': 0,
        'failed': 0,
        'errors': [],
    }

    for candidate_id in candidate_ids:
        try:
            result = pipeline_service.prepare_candidate(candidate_id)
            if result.get('success'):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'candidate_id': candidate_id,
                    'message': result.get('message')
                })
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'candidate_id': candidate_id,
                'message': str(e)
            })

    return results


@shared_task(queue='ebay_io', name='ebay.bulk_publish')
def bulk_publish(candidate_ids: List[int]) -> dict:
    """
    Publish multiple candidates to eBay.

    Queue: ebay_io
    Args:
        candidate_ids: List of EbayCandidate IDs

    Returns:
        Summary dict
    """
    results = {
        'total': len(candidate_ids),
        'success': 0,
        'failed': 0,
        'errors': [],
    }

    for candidate_id in candidate_ids:
        try:
            result = pipeline_service.publish_candidate(candidate_id)
            if result.get('success'):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'candidate_id': candidate_id,
                    'message': result.get('message')
                })
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'candidate_id': candidate_id,
                'message': str(e)
            })

    return results


@shared_task(queue='ebay_io', name='ebay.bulk_end')
def bulk_end(candidate_ids: List[int]) -> dict:
    """
    End multiple eBay listings.

    Queue: ebay_io
    Args:
        candidate_ids: List of EbayCandidate IDs

    Returns:
        Summary dict
    """
    results = {
        'total': len(candidate_ids),
        'success': 0,
        'failed': 0,
        'errors': [],
    }

    for candidate_id in candidate_ids:
        try:
            result = pipeline_service.end_candidate(candidate_id)
            if result.get('success'):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'candidate_id': candidate_id,
                    'message': result.get('message')
                })
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'candidate_id': candidate_id,
                'message': str(e)
            })

    return results


@shared_task(queue='pricing', name='ebay.bulk_reprice')
def bulk_reprice(candidate_ids: List[int]) -> dict:
    """
    Reprice multiple listings.

    Queue: pricing
    Args:
        candidate_ids: List of EbayCandidate IDs

    Returns:
        Summary dict
    """
    results = {
        'total': len(candidate_ids),
        'success': 0,
        'failed': 0,
        'errors': [],
        'price_changes': [],
    }

    for candidate_id in candidate_ids:
        try:
            result = pipeline_service.reprice_candidate(candidate_id)
            if result.get('success'):
                results['success'] += 1

                # Track price changes
                old_price = result.get('old_price')
                new_price = result.get('new_price')
                if old_price != new_price:
                    results['price_changes'].append({
                        'candidate_id': candidate_id,
                        'old_price': str(old_price),
                        'new_price': str(new_price),
                    })
            else:
                results['failed'] += 1
                results['errors'].append({
                    'candidate_id': candidate_id,
                    'message': result.get('message')
                })
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'candidate_id': candidate_id,
                'message': str(e)
            })

    return results


# Periodic tasks (for future use with celery beat)

@shared_task(queue='pricing', name='ebay.auto_reprice_all_listed')
def auto_reprice_all_listed() -> dict:
    """
    Automatically reprice all listed items.

    This task can be scheduled with celery beat to run periodically.

    Queue: pricing
    Returns:
        Summary dict
    """
    from .models import EbayCandidate

    # Get all listed candidates
    listed_candidates = EbayCandidate.objects.filter(status='listed').values_list('id', flat=True)

    # Trigger bulk reprice
    return bulk_reprice(list(listed_candidates))


@shared_task(queue='ebay_io', name='ebay.sync_sales')
def sync_sales() -> dict:
    """
    Sync sales from eBay and update inventory.

    This task can be scheduled with celery beat.

    Queue: ebay_io
    Returns:
        Summary dict
    """
    from django.core.management import call_command

    # Call the management command
    call_command('sync_ebay_sales')

    return {
        'success': True,
        'message': 'Sales sync completed'
    }
