==========
Change Log
==========
`unreleased`_
-------------------------------

`0.14.0`_ (2020-03-02)
-------------------------------
- Add endpoint to ask for transaction status
- Add endpoint to ask for meta-transaction status
- Improve performance of log listener by reducing the number of registered log listeners in the blockchain node.
  This should reduce cpu usage of the relay.
- Improve performance of user-events endpoint (:code:`users/<>/events`). THis should reduce the number of connections to the
  sql db and improve the response time.
- Remove :code:`__class__` field in events. This field was not meant to be there.


`0.13.1`_ (2020-02-28)
-------------------------------
- Bugfix: Set delegate gas price also for identity deployments

`0.13.0`_ (2020-02-27)
-------------------------------
- Improve performance of :code:`/networks` endpoint
- Allow delegate to set a gas price strategy in config. Supported are rpc (ask node via rpc), fixed (use a fixed gas price and bound (ask node, but set min/max limits)
- Allow to set connection method to node in config. Websockets and IPC were added to the already supported http method
- Docker: Expose relay default rest port

`0.12.1`_ (2020-02-23)
-------------------------------
- Fix delegate functionality with no unlocked account

`0.12.0`_ (2020-02-19)
-------------------------------
- Add config to enable/disable features of the relay server
- Change config schema, the old Schema does still work but is marked as deprecated and will be removed in future versions
- Change: Push notification will not mark messages as read, so there are still available to be retrieved later
- Change endpoint for getting balance to return wei instead of eth (BREAKING)
- Change meta-transaction schema to match new features in the contracts. (BREAKING) New fields: chainId, version, baseFee, gasPrice, gasLimit, feeRecipient, timeLimit, operationType. Fields removed: delegationFees, extraData
- Remove data content of push notification (BREAKING)
- Improve error messages of meta transaction related endpoints

`0.11.4`_ (2020-02-04)
-------------------------------
- Report errors to sentry

`0.11.3`_ (2020-01-29)
-------------------------------
- Make the relay server sign transactions
- Add endpoint to list all trustlines for a given user
- Enhance the log output

`0.11.2`_ (2020-01-20)
-------------------------------
- Add endpoint to get list of interests for trustline or user

`0.11.1`_ (2020-01-17)
-------------------------------
- Do not send push notifications twice

`0.11.0`_ (2020-01-15)
-------------------------------
- Update contracts to 1.0.0
- Update docs and handling of events for TrustlineUpdateCancel
- Update transfer related function signatures/events
- Remove unused outstanding fees fields
- Make delegation fees configurable via config.toml
- Add endpoint to query for fees of a meta-tx
- Add function for delegate to calculate fees for a meta-tx
- Prevent asking for a path in a frozen currency network

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
.. _0.11.0: https://github.com/trustlines-protocol/relay/compare/0.10.0...0.11.0
.. _0.11.1: https://github.com/trustlines-protocol/relay/compare/0.11.0...0.11.1
.. _0.11.2: https://github.com/trustlines-protocol/relay/compare/0.11.1...0.11.2
.. _0.11.3: https://github.com/trustlines-protocol/relay/compare/0.11.2...0.11.3
.. _0.11.4: https://github.com/trustlines-protocol/relay/compare/0.11.3...0.11.4
.. _0.12.0: https://github.com/trustlines-protocol/relay/compare/0.11.4...0.12.0
.. _0.12.1: https://github.com/trustlines-protocol/relay/compare/0.12.0...0.12.1
.. _0.13.0: https://github.com/trustlines-protocol/relay/compare/0.12.1...0.13.0
.. _0.13.1: https://github.com/trustlines-protocol/relay/compare/0.13.0...0.13.1
.. _0.14.0: https://github.com/trustlines-protocol/relay/compare/0.13.1...0.14.0
.. _unreleased: https://github.com/trustlines-protocol/relay/compare/0.14.0...master
