from web3 import Web3

from backend.settings import settings


def get_provider() -> Web3:
    provider = Web3(Web3.HTTPProvider(settings.web3_provider))
    # Ensure the web3 provider is set
    assert provider.is_connected(), "Web3 not connected"
    return provider
