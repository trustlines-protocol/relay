==========
Change Log
==========
`0.3.0`_ (not released yet)
-------------------------------
* web3 has been upgraded from 3.16.5 to 4.6.0.
* The spendable endpoints have been removed::

    /networks/<address:network_address>/users/<address:a_address>/spendable
    /networks/<address:network_address>/users/<address:a_address>/spendables/<address:b_address>

* The nonce is queried from the pending transaction. This will allow multiple
  transactions per block.
* The docker image is now based on ubuntu 18.04 and python 3.6

`0.2.0`_ (2018-08-21)
-------------------------------
* trustlines-relay has been released on PyPi
* the dependency on trustlines-contracts has been replaced with a dependency on
  trustlines-contracts-bin. trustlines-contracts-bin contains only the compiled
  contracts. The installation has become easier, since populus and solc isn't
  required anymore. Therefore tl-deploy isn't being installed anymore.

.. _0.2.0: https://github.com/trustlines-network/relay/compare/0.1.0...0.2.0
