# Running the trustlines system

This document explains how to run your own [trustlines network](https://trustlines.network/) relay server infrastructure. We will walk you through setting up a relay server and all dependent components. The current documentation is written for a Debian-based Linux system.

If you are low on time, you may jump to the description of the [docker-compose based setup](../docker/trustlines/README.md).

## Dependencies

Since the trustlines infrastructure components are implemented in python 3, you need to install relevant dependencies. You will need at least python 3.6.

```
sudo apt install build-essential python3-dev python3-venv pkg-config git libpq-dev
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
}
```

The directory called `config/` contains already prepared files for the different
networks of the foundation. Those include a list of addresses for the registered
currency networks. You can copy one of those files and adopt it to your needs,
in case you want to add custom deployed networks.

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
py-eth-index related commands has a working postgresql environment
configured.  All programs consider the `PG*` environment variables
(like `PGHOST`, `PGUSER`, ...) and will read `~/.pgpass` for
information about passwords. The [py-eth-index section](#py-eth-index)
describes how to create the trustlines specific tables.

### Creating a virtualenv

Run the following command to create a virtualenv:
```
mkdir -p ~/opt
python3 -mvenv ~/opt/trustlines-system
~/opt/trustlines-system/bin/pip install -U pip wheel setuptools
```

And activate the virtualenv with
```
source ~/opt/trustlines-system/bin/activate
```

This will add ~/opt/trustlines-system/bin to `PATH`. The following
steps assumes an acticated virtualenv.

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

And install py-eth-index
```
cd ~/py-eth-index
pip install -c constraints.txt .
```

#### Initializing the database
After the database has been created, it must be initialized. This can be done with the following command:
```
ethindex createtables
```

#### Importing the ABIs
We need to import the ABIs from the trustline-contracts. Trustlines-contracts is
installed as a dependency of the relay server. Please run the following only
after you have installed the relay server.

```
cp ~/opt/trustlines-system/trustlines-contracts/build/contracts.json ~
~/opt/py-eth-index/bin/ethindex importabi
```

#### Importing events
The following command will start importing all relevant events into the postgres
database:

```
ethindex runsync
```
This program will run forever.


### Relay server
#### Installation of the relay server

Clone the git repository and install it:
```
cd ~
git clone https://github.com/trustlines-protocol/relay
cd ~/relay
pip install -c constraints.txt .
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
tl-relay
```

However, this behaviour can be changed, you can check the options with:

```
tl-relay --help
```

The relay server needs access to the parity node and the PostgreSQL database.
`ethindex runsync` also has to be running for a fully functioning system.


#### Signing Transactions

The relay server needs to sign transactions. The default behaviour is
to rely on a Parity node with an unlocked account, that signs
transactions.

Alternatively the relay can sign transactions locally itself with a
configured key. For this approach add the following section to the
configuration file and adjust the values. The key is expected to be
encrypted in a keystore file. To unlock the key, a password file in
clear text must be provided as well.

```toml
[account]
keystore_path = "keystore.json"
keystore_password_path = "keystore-password.txt"
```
