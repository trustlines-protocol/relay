# trustlines relay server

## Installation

### Prerequisites
- Python 2.7
- pip

### Setup
```
git clone https://github.com/trustlines-network/relay.git
cd relay
pip install -r requirements.txt
export PYTHONPATH=`pwd`
export THREADING_BACKEND=gevent
```
We also need to deploy trustlines smart contracts on a local node or testrpc as described [here](https://github.com/trustlines-network/contracts).

Add the `address` of the deployed `Currency Network` to the `tokens` array in `/relay/config.json`:
```json
{
  "rpc":
  {
    "host": "localhost",
    "port": 8545,
    "ssl": false
  },
  "tokens": ["0x285ab3502b1187bb3d0ebcdf43d728a49561f181"]
}
```

### Usage
```
cd relay
python trustlines.py
```
