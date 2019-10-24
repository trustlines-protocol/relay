# Running the trustlines system

This document explains how to run your own [trustlines network](https://trustlines.network/) relay server infrastructure. We will walk you through setting up a relay server and all dependent components. The current documentation is written for a Debian-based Linux system.

If you are low on time, you may jump to the description of the [docker-compose based setup](../docker/trustlines/README.md).

## Dependencies

Since the trustlines infrastructure components are implemented in python 3, you need to install relevant dependencies. You will need at least python 3.6.

```
sudo apt install build-essential python3-dev python3-venv pkg-config \
     libssl-dev automake autoconf libtool libgraphviz-dev git libpq-dev
```

The installation instructions assume you create a dedicated user account and put
files directly into the user's home directory. Else, adapt the paths to your needs!

### Trustlines Blockchain

You need to run our modified parity node, which provides the JSONRPC API to the relay
server and the indexer. The documentation on how to run it can be found on the
[github page](https://github.com/trustlines-protocol/blockchain)
### Contracts
The [trustlines-contracts
repository](https://github.com/trustlines-protocol/contracts) contains the
solidity contracts to be deployed on the blockchain and a commandline tool to deploy the contracts. The [how to deploy the
contracts guide](https://github.com/trustlines-protocol/contracts) contains more information on how to deploy the contracts.
The tool will return the addresses of the deployed contracts. You need to provide that information to the relay server with as json file `addresses.json` with the following format:

```
{
  "networks":
  [<list of currency network addresses>],
  "unwEth": <address of unw_eth_contract>,
  "exchange": <address of exchange>
}
```

For the already deployed contracts on the trustlines blockchain use this file:
```
{
  "networks":
  [
    "0x9750bdB86B32DCaeFEAea4f29857D52C8d848860",
    "0xe4D3cEB3d59B6Fa4a39C8D9525c84C79057C1e29",
    "0xd75C9C8a79D6a85d4923b7C16BAb144cC9BB48e4"
  ]
}
```

We assume from now on that the contracts have already been deployed
and that the `addresses.json` file has been copied to the user's home directory.

### PostgreSQL
The trustlines system uses a PostgreSQL database to store some user data and to
keep a synchronized view on the relevant state from the blockchain.

Install PostgreSQL with:
```
sudo apt install postgresql
```

After this, a database user must be created. Please use a real password:
```
sudo -u postgres psql <<EOF
CREATE USER trustlines WITH PASSWORD 'choose-a-password-here';
ALTER USER trustlines CREATEDB;
EOF
```

Next, the postgres environment should be configured for the account running
the relay server:
```
echo >>~/.pgpass 'localhost:5432:*:trustlines:choose-a-password-here'; chmod 0600 ~/.pgpass
cat >>~/.bashrc <<EOF
export PGUSER=trustlines
export PGHOST=localhost
export PGDATABASE=trustlinesdb
EOF
```

After logging in again, in order to have the environment variables set, the user
should be able to create the database:

```
createdb trustlinesdb
```

The rest of this tutorial assumes that the user running the relay and
py-eth-index related commands has a working postgresql environment configured.
All programs consider the PG* environment variables and will read ~/.pgpass for
information about passwords. The [py-eth-index section](#py-eth-index) describes
how to create the trustlines specific tables.

### Py-eth-index
The [py-eth-index repository](https://github.com/trustlines-protocol/py-eth-index)
contains a helper program that synchronizes the relevant information from the
blockchain into a postgresql database.

#### Installation of py-eth-index

Clone the git repository:
```
cd ~
git clone https://github.com/trustlines-protocol/py-eth-index
```
Let’s create a virtualenv for this repository:
```
python3 -m venv ~/opt/py-eth-index; ~/opt/py-eth-index/bin/pip install -U pip
```
and install py-eth-index
```
cd ~/py-eth-index
~/opt/py-eth-index/bin/pip install -c constraints.txt -r requirements.txt
~/opt/py-eth-index/bin/pip install -c constraints.txt .
```
#### Initializing the database
After the database has been created, it must be initialized. This can be done with the following command:

```
~/opt/py-eth-index/bin/ethindex createtables
```
#### Importing the ABIs
We need to import the ABIs from the trustline-contracts. Trustlines-contracts is
installed as a dependency of the relay server. Please run the following only
after you have installed the relay server.

```
cp ~/opt/relay/trustlines-contracts/build/contracts.json ~
~/opt/py-eth-index/bin/ethindex importabi
```

#### Importing events
The following command will start importing all relevant events into the postgres
database:

```
~/opt/py-eth-index/bin/ethindex runsync
```
This program will run forever.


### Relay server
#### Prerequisites for the installation

-  Python 3.6 or up
-  pip

Installation on Ubuntu

    sudo apt install build-essential python3-dev libsecp256k1-dev python3-virtualenv virtualenv pkg-config libssl-dev automake autoconf libtool libgraphviz-dev git




#### Installation of the relay server

Clone the git repository, create a virtualenv and install into
that.
```
cd ~
git clone https://github.com/trustlines-protocol/relay
python3 -m venv ~/opt/relay; ~/opt/relay/bin/pip install -U pip
cd ~/relay;
~/opt/relay/bin/pip install -c constraints.txt -r requirements.txt
~/opt/relay/bin/pip install -c constraints.txt .
```

#### Running the relay server

The relay server needs the addresses of the deployed contracts. In case you've
deployed your own contracts, please copy addresses.json to `~`.

We will also need a config file. You can use the one from the git checkout:

```
cp ~/relay/config.toml ~
```

The relay server reads both files from the current directory per default,
so we need to start it where those files have been copied to:

```
cd ~
~/opt/relay/bin/tl-relay
```

However, this behaviour can be changed, you can check the options with:

```
cd ~
~/opt/relay/bin/tl-relay --help
```

The relay server needs access to the parity node and the PostgreSQL database.
`ethindex runsync` also has to be running for a fully functioning system.
