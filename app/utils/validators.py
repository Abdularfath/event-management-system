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
def validate_event(data):
    # TODO: implement on Day 6
    return []
 
 
# ── Ticket type validator (stub — will be filled on Day 8) ──────────
def validate_ticket_type(data):
    # TODO: implement on Day 8
    return []
