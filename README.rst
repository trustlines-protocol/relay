trustlines relay server
=======================

Installation
------------

Prerequisites
~~~~~~~~~~~~~

-  Python 3.6 or up
-  pip

Installation on Ubuntu
^^^^^^^^^^^^^^^^^^^^^^

::

    sudo apt install build-essential python3-dev libsecp256k1-dev python3-virtualenv virtualenv pkg-config libssl-dev automake autoconf libtool libgraphviz-dev git



Setup
~~~~~

::

    git clone https://github.com/trustlines-network/relay.git
    cd relay
    pip install -c constraints.txt -r requirements.txt
    pip install -c constraints.txt -e .

We also need to deploy trustlines smart contracts on a local node or
testrpc as described
`here <https://github.com/trustlines-network/contracts>`__.

Add the ``address`` of the deployed ``Currency Network`` to the file
``/relay/networks``:

Usage
~~~~~

::

    cd relay
    python trustlines.py

Docs
----

-  `REST API Documentation <./docs/RelayAPI.md>`__

Change log
----------

See `CHANGELOG <https://github.com/trustlines-network/relay/blob/develop/CHANGELOG.rst>`_.
