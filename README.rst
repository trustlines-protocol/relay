.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: https://circleci.com/gh/trustlines-protocol/relay.svg?style=svg
    :target: https://circleci.com/gh/trustlines-protocol/relay

.. image:: https://badges.gitter.im/Join%20Chat.svg
    :target: https://gitter.im/trustlines/community

Trustlines relay server
=======================
The Trustlines relay server is a component of the `Trustlines Protocol <https://trustlines.foundation/protocol.html>`__.
The Trustlines Protocol is a set of rules to allow the transfer of value on top of existing trust
relationships stored on a trustless infrastructure, e.g. a blockchain.

In the technology stack, the relay server is located in between a client of the Trustlines Protocol,
e.g. a mobile app build on to of the `Trustlines clientlib <https://github.com/trustlines-protocol/clientlib>`__, and the deployed
`Trustlines smart contracts <https://github.com/trustlines-protocol/contracts>`__ on a chosen blockchain, e.g.
`The Trustlines Blockchain (TLBC) <https://explore.tlbc.trustlines.foundation>`__.

Operating a relay server requires an ethereum based blockchain node, a postgres database
and a `py-eth-index
<https://github.com/trustlines-protocol/py-eth-index>`__
instance that index events that the relay will be able to process and serve to its users.

The goal of the relay server is to handle computation and services which are currently not feasible to do on the client
or on the blockchain.
More specifically the relay currently handles:

- Computing a graph of the trustlines in a currency networks
- Computing the path of mediators for trustlines transfer in this graph
- Providing an api to get a user events regarding trustlines
- Deploying identity contracts for users
- Relaying transactions of the user to a blockchain node
- Paying for meta-transactions of a user in exchange for a fee
- Sending notifications for user events.

Depending on the use case it is possible to enable/disable some of the functionality.

Try it out
----------
If you just want to inspect what you can do with the relay server, have a look at the `ReST API Documentation <docs/RelayAPI.md>`_
and try it out for example with the relay server running at `https://tlbc.relay.anyblock.tools`.
To get the list of registered networks, try::

    curl https://tlbc.relay.anyblock.tools/api/v1/networks

Get Up and Running
------------------

Via docker-compose
~~~~~~~~~~~~~~~~~~
The fastest way to run a relay server is via docker-compose. The only pre-requisites on your system are
docker and docker-compose. Please note that we officially only support Linux, however other systems with docker should
work as well. For instructions, please view the
`relay docker instructions <docker/trustlines/README.md>`__.

Manual Installation
~~~~~~~~~~~~~~~~~~~~

An installation of the relay server requires at least the following
components:

- PostgreSQL header files
- Python 3.6 or up
- pip

To install the relay server on Ubuntu 18.04, start by installing the pre-requisites
with the following command::

    sudo apt install build-essential python3 python3-pip python3-dev libsecp256k1-dev \
    python3-virtualenv virtualenv pkg-config libssl-dev automake \
    autoconf libtool git libpq-dev


To install the relay, start by cloning the repository::

    git clone https://github.com/trustlines-protocol/relay.git
    cd relay

Then create and activate a fresh virtualenv::

    virtualenv -p python3 venv
    source venv/bin/activate

Finally, to install all needed dependencies to run the relay, use the following command::

    pip install -r requirements.txt -e .

You can verify that the relay is correctly installed by running `tl-relay --help`
to get an overview of available options.


Additional dependencies
~~~~~~~~~~~~~~~~~~~~~~~
In addition to having installed the relay, you will need a blockchain
node connected to a chain with deployed `trustlines contracts
<https://github.com/trustlines-protocol/contracts>`__
to interact with. You can go to the `contracts repository
<https://github.com/trustlines-protocol/contracts>`__
to see how to deploy new trustlines contracts, or you may use the provided
:code:`addresses.json` files in `config/` containing addresses of deployed contracts on the Trustlines Blockchain by
copying them here::

    cp config/addresses_tlbc.json addresses.json

You may use the `blockchain repository
<https://github.com/trustlines-protocol/blockchain>`__
to get a Trustlines Blockchain node running.

The relay also uses a `py-eth-index
<https://github.com/trustlines-protocol/py-eth-index>`__
instance that index events that the relay will be able to process and serve to its users.

Configuration
~~~~~~~~~~~~~

The relay server can be configured via a :code:`config.toml` file.
You can find an example config in this repository: :code:`config.toml`.
Notably, the connection to the running blockchain node required by the relay
can be configured via the keys under :code:`[node_rpc]`::

    [node_rpc]
    ## Possible values for connection type are ipc, http, websocket. Default: http
    ## type = websocket
    port = 8545
    host = "localhost"
    use_ssl = false
    ## or use an uri to automatically detect the correct provider. Example for ipc:
    # uri = "file:///path-to-file.ipc"

Additionally, if the delegate service is enabled, the relay relies on an unlocked account
on the connected node to sign transactions. This behaviour can be changed with the :code:`[account]` keys::

    [account]
    keystore_path = "keystore.json"
    keystore_password_path = "keystore-password.txt"

In parallel to the config, the relay needs to know the addresses of deployed trustlines contracts.
That is, which currency networks are deployed on the chain and the relay should let its users interact with,
and which identity proxy factory the relay agrees to use to deploy identities for its users.
You can find a example of the :code:`addresses.json` file in this repository.
This file contains the addresses of already deployed currency networks and identity proxy factory on the
Trustlines Blockchain.

Once configured, the relay can be started with the command :code:`tl-relay`.
You can verify that it is correctly running with::

    curl http://localhost:5000/api/v1/version

Start developing
----------------
If you want to start fiddling around with the code, you need to install the relay and the dev requirements.
Start by cloning the repository::

    git clone https://github.com/trustlines-protocol/relay.git
    cd relay

And install the relay and its development dependencies::

    pip install -r dev-requirements.txt -r requirements.txt -e .

You can run the tests on the relay with::

    ./pytest

You can also run end2end tests that will test how the contracts, relay, and clientlib
work together. For more information about the end2end tests, see
`the end2end repository
<https://github.com/trustlines-protocol/end2end>`__

Contributing
------------
Contributions are highly appreciated, but please check our `contributing guidelines </CONTRIBUTING.md>`__.

Pre-commit hooks
~~~~~~~~~~~~~~~~

You should consider initializing the pre-commit hooks. The
installed git pre-commit hooks run flake8 and black among other things
when committing changes to the git repository.
Install them with ::

    pre-commit install

You can run them on all files with::

    pre-commit run -a

Dependencies
~~~~~~~~~~~~
To manage and pin the (sub)dependencies of the relay server we use
`pip-tools <https://github.com/jazzband/pip-tools/>`__.
We create two requirements files, one for the production environment (:code:`requirements.txt`)
and one for the additional development requirements (:code:`dev-requirements.txt`).
For the dev environment, you have to install both. The production dependencies are derived
from the dependencies defined in :code:`setup.py` and constraint by :code:`constraints.in`.
To add new dependencies, add them to :code:`setup.py` and then run :code:`./compile-requirements`.
If wrong subdependencies create problems, you can restrict them with :code:`constraints.in`.
The development requirements are derived from :code:`dev-requirements.in`. To add new development
dependencies, add them to this file and then rerun :code:`./compile-requirements`.
To upgrade the dependencies in the created requirement files, check out the available options
for pip-tools and pass them to the compile script. To update all dependencies,
run :code:`./compile-requirements.sh --upgrade`.

Release
~~~~~~~
For versioning we use `setuptools-scm <https://pypi.org/project/setuptools-scm/>`_. This means the version number is
derived from git tags. To release a new version of the relay on PyPI or Docker Hub, simply tag a commit with a valid version
number either via git, or from `github <https://github.com/trustlines-protocol/relay/releases/new>`_.
Make sure to update the changelog accordingly and add all changes since the last released version.

Change log
----------

See `CHANGELOG <CHANGELOG.rst>`_.

Documentation
-------------

If you're trying to setup a complete trustlines system, please visit
`Running the trustlines system.
<docs/RelayServer.md>`_

The relay server provides a REST API. Please visit the `REST API
Documentation
<docs/RelayAPI.md>`_
page for more information.
