from .models import UserProfile

# Example pool of pre-generated TRC20 addresses
PREGENERATED_WALLETS = [
    "TG3XXX...",  # Add your list here
    "TX1XXX...",
    # ...
]

def assign_wallet_address_to_user(user):
    # Simple method: find unused wallet
    used_addresses = UserProfile.objects.exclude(trc20_wallet_address__isnull=True).values_list('trc20_wallet_address', flat=True)
    for address in PREGENERATED_WALLETS:
        if address not in used_addresses:
            return address
    raise Exception("No available TRC20 addresses left.")
