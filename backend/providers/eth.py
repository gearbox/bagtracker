from web3 import Web3

from backend.settings import settings, Web3Providers


def get_provider(provider_name: str | None = None) -> Web3:
    if provider_name:
        try:
            provider_url = Web3Providers[provider_name].value
        except KeyError:
            raise ValueError(f"Unknown provider: {provider_name}")
    else:
        provider_url = settings.web3_provider

    provider = Web3(Web3.HTTPProvider(provider_url.replace("<API_KEY>", settings.infura_api_key or "")))
    # Ensure the web3 provider is set
    assert provider.is_connected(), "Web3 not connected"
    return provider


class ProvidersManager:
    def __init__(self):
        self.providers = {}

    def get_provider(self, provider_name: str | None = None) -> Web3:
        if provider_name:
            try:
                provider_url = Web3Providers[provider_name].value

            except KeyError:
                raise ValueError(f"Unknown provider: {provider_name}")
        else:
            provider_url = settings.web3_provider

        provider = Web3(Web3.HTTPProvider(provider_url))
        # Ensure the web3 provider is set
        assert provider.is_connected(), "Web3 not connected"
        return provider
