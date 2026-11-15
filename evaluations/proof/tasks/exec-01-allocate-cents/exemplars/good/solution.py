def allocate(total_cents, weights):
    if any(w < 0 for w in weights):
        raise ValueError('negative weight')
    if not weights:
        if total_cents:
            raise ValueError('nothing to allocate to')
        return []
    if total_cents < 0:
        return [-x for x in allocate(-total_cents, weights)]
    if not any(weights):
        weights = [1] * len(weights)
    whole = sum(weights)
    shares = [total_cents * w // whole for w in weights]
    order = sorted(range(len(weights)),
                   key=lambda i: (-(total_cents * weights[i] % whole), -weights[i], i))
    for i in order[:total_cents - sum(shares)]:
        shares[i] += 1
    return shares
