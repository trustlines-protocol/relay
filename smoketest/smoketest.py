import requests


API_URL = 'http://localhost:5000/api/v1/'


def test_tokens():
    url = 'networks'

    result = requests.get(API_URL + url).json()

    assert len(result) == 3
    assert len([network for network in result if network['name'] == 'Testcoin']) == 1


def test_exchanges():
    url = 'exchange/exchanges'

    result = requests.get(API_URL + url).json()

    assert len(result) == 1
