trustlines relay server
=======================

Installation
------------

Prerequisites
~~~~~~~~~~~~~

-  Python 3.5 or up
-  pip

Installation on Ubuntu
^^^^^^^^^^^^^^^^^^^^^^

::

    sudo apt install build-essential python3-dev python3-virtualenv virtualenv pkg-config libssl-dev automake autoconf libtool libgraphviz-dev git

One of the dependencies used in the relay server is the secp256k1
library. If you're using python 3.5 on linux you can skip the folowing
step, since pypi contains binary packages for secp256k1. If not, you'll
have to run the following to install the secp256k1 C library:

::

    git clone https://github.com/bitcoin-core/secp256k1.git
    cd secp256k1
    ./autogen.sh
    ./configure --enable-module-recovery
    make
    sudo make install
    sudo ldconfig

Setup
~~~~~

Download solc and install it into ~/bin:

::

    curl -L -o $HOME/bin/solc https://github.com/ethereum/solidity/releases/download/v0.4.21/solc-static-linux && chmod +x $HOME/bin/solc

::

    git clone https://github.com/trustlines-network/relay.git
    cd relay
    pip install -c constraints.txt populus
    pip install -c constraints.txt -r requirements.txt
    pip install -c constraints.txt -e .
    export PYTHONPATH=`pwd`
    export THREADING_BACKEND=gevent

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
