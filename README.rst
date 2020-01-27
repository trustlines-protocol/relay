|Code style: black|

.. image:: https://circleci.com/gh/trustlines-protocol/relay.svg?style=svg
    :target: https://circleci.com/gh/trustlines-protocol/relay

trustlines relay server
=======================
This documents describes how to install the trustlines relay server
for local development.

If you're trying to setup a complete trustlines system, please visit
`Running the trustlines system
<https://github.com/trustlines-protocol/relay/blob/master/docs/RelayServer.md>`__

The relay server provides a REST API. Please visit the `REST API
Documentation
<https://github.com/trustlines-protocol/relay/blob/master/docs/RelayAPI.md>`__
page for more information.


Installation
------------

Prerequisites
~~~~~~~~~~~~~

An installation of the relay server requires at least the following
components:

- PostgreSQL header files
- Python 3.6 or up
- pip

Installation on Ubuntu
^^^^^^^^^^^^^^^^^^^^^^
Please issue the following command to install the prerequisites on ubuntu 18.04::

    sudo apt install build-essential python3-dev libsecp256k1-dev \
    python3-virtualenv virtualenv pkg-config libssl-dev automake \
    autoconf libtool git libpq-dev


Setup
~~~~~
To install all needed development dependencies run the following commands in a
fresh virtualenv::

    git clone https://github.com/trustlines-protocol/relay.git
    cd relay
    pip install -c constraints.txt -r requirements.txt
    pip install -c constraints.txt -e .

If you plan to make changes to the source code and open pull requests
on github, please consider initializing the pre-commit hooks. The
installed git pre-commit hooks run flake8 and black among other things
when committing changes to the git repository ::

    pre-commit install
    pre-commit run -a

After running those commands, the relay server is ready to run. Please
run `tl-relay --help` to get an overview of available options.

Change log
----------

See `CHANGELOG <https://github.com/trustlines-protocol/relay/blob/master/CHANGELOG.rst>`_.

.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
