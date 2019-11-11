==========
Change Log
==========
`0.11.0`_ (unreleased)
-------------------------------
`0.10.0`_ (2019-11-05)
-------------------------------
- Add make logging configurable via the TOML configuration file
- Remove gas estimation on find path requests (BREAKING)
- Change: deploy identity requests are only allowed for known identity factories (BREAKING)
- Change config file format to TOML
- Fix an issue that identity deployment did not work when two identity were deployed in the same block.

`0.9.0`_ (2019-10-05)
-------------------------------
* Change identities endpoint to deploy identity contracts with deterministic addresses via a factory contract
* Change identities endpoint to deploy identity contracts as proxies to an implementation contract. Reduces the gas cost of deployment
* Change the arguments of identities endpoint (BREAKING)
* Increase debug output for push notifications
`0.8.1`_ (2019-10-03)
-------------------------------
* Fix a bug in the push notification service that was introduced by the marshmallow upgrade in 0.7.0
`0.8.0`_ (2019-10-01)
-------------------------------
* Upgrade metatransactions to use fees (BREAKING)
* Add version ReST endpoint
* Fix an encoding problem in the ReST api
* Fix a problem that could lead to a deadlock in the push notification database
`0.7.0`_ (2019-09-02)
-------------------------------
* Update marshmallow and other related dependencies
* Update path finding to ignore frozen trustlines
* Add information related to frozen trustlines to API
* Update web3 to version 5.0.0 and other dependencies
* Improve local view of Currency Networks graphs
* Add extraData to transfers and Transfer events (BREAKING)

`0.6.1`_ (2019-03-15)
-------------------------------
* Add an option to set the gasprice calculation method. This is necessary if the rpc endpoint by parity is too slow.

`0.6.0`_ (2019-03-14)
-------------------------------
* Allow find_path to search for paths for receiver pays transfers
* Fixed a bug, where the time being slighly off resulted in an internal server error

`0.5.0`_ (2019-02-18)
-------------------------------
* implement meta transaction related functionality
* reduce CPU usage
* refactor usage of time.time() calls inside graph

`0.4.1`_ (2019-01-25)
-------------------------------
* fix broken dependency on old version of trustlines-contracts-bin

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

.. _0.2.0: https://github.com/trustlines-protocol/relay/compare/0.1.0...0.2.0
.. _0.3.0: https://github.com/trustlines-protocol/relay/compare/0.2.0...0.3.0
.. _0.4.0: https://github.com/trustlines-protocol/relay/compare/0.3.0...0.4.0
.. _0.4.1: https://github.com/trustlines-protocol/relay/compare/0.4.0...0.4.1
.. _0.5.0: https://github.com/trustlines-protocol/relay/compare/0.4.1...0.5.0
.. _0.6.0: https://github.com/trustlines-protocol/relay/compare/0.5.0...0.6.0
.. _0.6.1: https://github.com/trustlines-protocol/relay/compare/0.6.0...0.6.1
.. _0.7.0: https://github.com/trustlines-protocol/relay/compare/0.6.1...0.7.0
.. _0.8.0: https://github.com/trustlines-protocol/relay/compare/0.7.0...0.8.0
.. _0.8.1: https://github.com/trustlines-protocol/relay/compare/0.8.0...0.8.1
.. _0.9.0: https://github.com/trustlines-protocol/relay/compare/0.8.1...0.9.0
.. _0.10.0: https://github.com/trustlines-protocol/relay/compare/0.9.0...0.10.0
.. _0.11.0: https://github.com/trustlines-protocol/relay/compare/0.10.0...master
