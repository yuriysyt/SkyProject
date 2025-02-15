import random
import string

def generate_random_token(length=32):
    Generate a random token string.
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def calculate_health_score(responses):
    Calculate an overall health score based on responses.
    if not responses:
        return 0
    total = sum(r.value for r in responses if hasattr(r, 'value'))
    return round(total / len(responses) * 10) / 10

