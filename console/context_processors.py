from console.mark import mark_icon_url, mark_mask_url


def ledger(request):
    """The wordmark's mask, built from the one mark shape (console/mark.py)."""
    return {"mark_mask_url": mark_mask_url(), "mark_icon_url": mark_icon_url()}
