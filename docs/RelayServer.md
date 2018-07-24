# Running the trustlines system

This document explains how to run your own [trustlines network](https://trustlines.network/) relay server infrastructure. We will walk you through setting up a relay server and all dependent components. The current documentation is written for a Debian-based Linux system.

If you are low on time, you may jump to the description of the [docker-compose based setup](#docker-compose-based-setup).

## Dependencies

Since the trustlines infrastructure components are implemented in python 3, you need to install relevant dependencies.

```
sudo apt install build-essential python3-dev python3-venv pkg-config \
     libssl-dev automake autoconf libtool libgraphviz-dev git libpq-dev
```

The installation instructions assume you create a dedicated user account and put
files directly into the user's home directory. Else, adapt the paths to your needs!

### Parity

You need to run a parity node, which provides the JSONRPC API to the relay
server and the indexer. At the moment we recommend using parity together with
the kovan chain.

Please follow the [official documentation](https://wiki.parity.io/Setup) in
order to install parity. Paritytech provides [binary
releases](https://github.com/paritytech/parity-ethereum/releases).

```
curl -O https://releases.parity.io/v1.11.7/x86_64-unknown-linux-gnu/parity_1.11.7_ubuntu_amd64.deb
sudo dpkg -i parity_1.11.7_ubuntu_amd64.deb
```

The relay server needs an unlocked account. Therefore, make sure you're not
exposing the JSONRPC endpoint. By default parity listens on the local interface
for new connections, so any user with a login on the machine could also access
the JSONRPC endpoint.


The following command line starts parity with the kovan chain. Please adapt the
--author, --unlock and --password arguments

```
parity --no-warp --auto-update none --no-download --chain kovan \
    --author 0x987654321 --unlock 0x987654321 --password /path/to/password-file \
    --jsonrpc-hosts all
```

One command line option we like to highlight is the `--no-warp` option. If you
don't specify this option, parity will enable 'Warp Synchronization'. Warp
synchronization allows for a faster synchronization, but the relay server will
not work reliably with this feature turned on. The [official documentation](https://wiki.parity.io/Getting-Synced#warp-synchronization)
contains a description of the behaviour that is problematic:

> Note, at present, snapshotting does not place all of the block or receipt data
> into the database. This means you will not get information relating to
> transactions more than a few days old.

So, please double check that warp synchronization is turned off when using
parity. The whole trustlines system may appear to work, but will give wrong
results if you run with warp mode enabled.

### Contracts
The [trustlines-contracts
repository](https://github.com/trustlines-network/contracts) contains the
solidity contracts to be deployed on the blockchain. The ('how to deploy the
contracts guide')[https://github.com/trustlines-network/contracts] contains more information on how to deploy the contracts. We assume from now on that the contracts have already been deployed
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
The [py-eth-index repository](https://github.com/trustlines-network/py-eth-index)
contains a helper program that synchronizes the relevant information from the
blockchain into a postgresql database.

#### Installation of py-eth-index

Clone the git repository:
```
cd ~
git clone https://github.com/trustlines-network/py-eth-index
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
##### secp256k1
One of the dependencies used in the relay server is the secp256k1 library. If
you're using python 3.5 on linux you can skip the following step, since pypi
contains binary packages for secp256k1. If not, you will have to run the following commands
to install the secp256k1 C library:

```
git clone https://github.com/bitcoin-core/secp256k1.git
cd secp256k1
./autogen.sh
./configure --enable-module-recovery
make
sudo make install
sudo ldconfig
```

##### Solidity
```
curl -L -o $HOME/bin/solc https://github.com/ethereum/solidity/releases/download/v0.4.21/solc-static-linux && chmod +x $HOME/bin/solc
```

#### Installation of the relay server

Clone the git repository, create a virtualenv and install into
that. Please note that we cannot reuse the py-eth-index virtualenv, since both
projects have conflicting dependencies.
```
cd ~
git clone https://github.com/trustlines-network/relay
python3 -m venv ~/opt/relay; ~/opt/relay/bin/pip install -U pip
cd ~/relay;
~/opt/relay/bin/pip install -c constraints.txt populus
~/opt/relay/bin/pip install -c constraints.txt -r requirements.txt
~/opt/relay/bin/pip install -c constraints.txt .
```

#### Running the relay server

The relay server needs the addresses of the deployed contracts. In case you've
deployed your own contracts, please copy addresses.json to `~`.

We will also need a config file. You can use the one from the git checkout:

```
cp ~/relay/config.json ~
```

The relay server reads both files from the current directory, so we need to start it where those files have been copied to:

```
cd ~
THREADING_BACKEND=gevent ETHINDEX=1 ~/opt/relay/bin/tl-relay
```

The relay server needs access to the parity node and the PostgreSQL database.
`ethindex runsync` also has to be running for a fully functioning system.
