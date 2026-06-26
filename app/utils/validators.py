# ── Venue validator ─────────────────────────────────────────────────
def validate_venue(data):
    """
    Validate venue form data.
    Returns a list of error strings.
    Empty list means validation passed.
    """
    errors = []
 
    name = data.get('name', '').strip()
    address = data.get('address', '').strip()
    city = data.get('city', '').strip()
    capacity = data.get('capacity', '').strip()
 
    if not name:
        errors.append('Venue name is required.')
    elif len(name) < 3:
        errors.append('Venue name must be at least 3 characters.')
    elif len(name) > 100:
        errors.append('Venue name must be under 100 characters.')
 
    if not address:
        errors.append('Address is required.')
 
    if not city:
        errors.append('City is required.')
 
    if not capacity:
        errors.append('Capacity is required.')
    else:
        try:
            cap = int(capacity)
            if cap < 1:
                errors.append('Capacity must be at least 1.')
            elif cap > 1000000:
                errors.append('Capacity value seems unrealistically large.')
        except ValueError:
            errors.append('Capacity must be a whole number.')
 
    return errors
 
 
# ── Event validator (stub — will be filled on Day 6) ────────────────
from datetime import datetime
 
def validate_event(data):
    """
    Validate event form data.
    Returns a list of error strings. Empty = passed.
    """
    errors = []
 
    name        = data.get('name','').strip()
    description = data.get('description','').strip()
    start_str   = data.get('start_datetime','').strip()
    end_str     = data.get('end_datetime','').strip()
    venue_id    = data.get('venue_id','').strip()
    event_type  = data.get('event_type','').strip()
 
    # Name
    if not name:
        errors.append('Event name is required.')
    elif len(name) < 3:
        errors.append('Event name must be at least 3 characters.')
    elif len(name) > 150:
        errors.append('Event name must be under 150 characters.')
 
    # Description
    if not description:
        errors.append('Description is required.')
 
    # Venue
    if not venue_id:
        errors.append('Please select a venue.')
 
    # Event type
    if event_type not in ['physical', 'virtual', 'hybrid']:
        errors.append('Please select a valid event type.')
 
    # Dates — parse and compare
    start_dt = end_dt = None
    fmt = '%Y-%m-%dT%H:%M'  # HTML datetime-local format
    if not start_str:
        errors.append('Start date and time is required.')
    else:
        try:
            start_dt = datetime.strptime(start_str, fmt)
        except ValueError:
            errors.append('Invalid start date format.')
 
    if not end_str:
        errors.append('End date and time is required.')
    else:
        try:
            end_dt = datetime.strptime(end_str, fmt)
        except ValueError:
            errors.append('Invalid end date format.')
 
    if start_dt and end_dt:
        if end_dt <= start_dt:
            errors.append('End date must be after start date.')
 
    return errors

 
 
# ── Ticket type validator (stub — will be filled on Day 8) ──────────
def validate_ticket_type(data):
    """
    Validate ticket type form data.
    Returns list of error strings. Empty = passed.
    """
    errors = []
 
    name       = data.get('name','').strip()
    price      = data.get('price','').strip()
    qty_total  = data.get('quantity_total','').strip()
    max_order  = data.get('max_per_order','').strip()
 
    # Name
    if not name:
        errors.append('Ticket name is required.')
    elif len(name) > 80:
        errors.append('Ticket name must be under 80 characters.')
 
    # Price
    if price == '':
        errors.append('Price is required. Enter 0 for free tickets.')
    else:
        try:
            p = float(price)
            if p < 0:
                errors.append('Price cannot be negative.')
            elif p > 999999:
                errors.append('Price seems unrealistically high.')
        except ValueError:
            errors.append('Price must be a number.')
 
    # Quantity total
    if not qty_total:
        errors.append('Total quantity is required.')
    else:
        try:
            q = int(qty_total)
            if q < 1:
                errors.append('Total quantity must be at least 1.')
        except ValueError:
            errors.append('Total quantity must be a whole number.')
 
    # Max per order
    if not max_order:
        errors.append('Max per order is required.')
    else:
        try:
            m = int(max_order)
            if m < 1:
                errors.append('Max per order must be at least 1.')
            # Validate max <= total only when both are valid numbers
            elif qty_total.isdigit() and m > int(qty_total):
                errors.append('Max per order cannot exceed total quantity.')
        except ValueError:
            errors.append('Max per order must be a whole number.')
 
    return errors

