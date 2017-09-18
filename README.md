# trustlines relay server

## Installation

### Prerequisites
- Python 3.5
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

Add the `address` of the deployed `Currency Network` to the file `/relay/networks`:


### Usage
```
cd relay
python trustlines.py
```
