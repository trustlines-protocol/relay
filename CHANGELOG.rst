==========
Change Log
==========
`0.4.0`_ (2019-01-24)
-------------------------------
* new endpoint for trustline closing has been added, the reduce debt endpoint
  has been removed
* the used contracts package has been upgraded
* the internal path finding and fee computation has been enhanced to support
  payments without fees for the last hop
* a payment method, where the receiver pays fees, has been added
* max capacity path calculation has been fixed
* tl-relay now parses command line arguments

`0.3.0`_ (2018-11-16)
-------------------------------
* web3 has been upgraded from 3.16.5 to 4.7.1. As a result you should be able to
  install py-eth-index and trustlines-watch into the same virtualenv.
  Also `THREADING_BACKEND` doesn't have to be set anymore.
* `ETHINDEX` doesn't have to be set anymore. The relay server uses the ethindex
  backend by default.
* A gevent aware wrapper of pytest has been added. Please run `./pytest` inside
  the relay repository now.
* The spendable endpoints have been removed::

    /networks/<address:network_address>/users/<address:a_address>/spendable
    /networks/<address:network_address>/users/<address:a_address>/spendables/<address:b_address>

* The nonce is queried from the pending transaction. This will allow multiple
  transactions per block. Please make sure to start parity with the
  `--jsonrpc-apis=all` or `--jsonrpc-apis=parity` option.
* The docker image is now based on ubuntu 18.04 and python 3.6
* Add option to syncronize the sending of transactions if env TRUSTLINES_SYNC_TX_RELAY
  is set, because of a bug in parity
* Require python version >= 3.6
* Add interests:
  The returned balances include an estimation of the interests
  Can work with Trustline Updates that include interests
  Breaks backwardscompatibilty, will not work anymore with old contracts without interests
* Add first version of endpoint to find a path to close a trustline via a rebalancing of the
  trustlines.

`0.2.0`_ (2018-08-21)
-------------------------------
* trustlines-relay has been released on PyPi
* the dependency on trustlines-contracts has been replaced with a dependency on
  trustlines-contracts-bin. trustlines-contracts-bin contains only the compiled
  contracts. The installation has become easier, since populus and solc isn't
  required anymore. Therefore tl-deploy isn't being installed anymore.

.. _0.2.0: https://github.com/trustlines-network/relay/compare/0.1.0...0.2.0
.. _0.3.0: https://github.com/trustlines-network/relay/compare/0.2.0...0.3.0
.. _0.4.0: https://github.com/trustlines-network/relay/compare/0.3.0...0.4.0
