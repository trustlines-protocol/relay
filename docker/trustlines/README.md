# trustlines running via docker-compose

This directory contains the files needed to start a trustlines system via
docker-compose.

## Services
The docker-compose file contains service definitions for the following services:

- db
A service running a postgres server. The postgres files will be stored in the
`postgres-data` docker volume.

- tlbc
A service running a modified parity node for the trustlines blockchain. The blockchain data will be
stored in the `blockchain-data` docker volume.

- index
A service running py-eth-index, which synchronizes certain information from parity into the postgres database.

- relay
The relay server itself.

## Setup
We need to do some initial setup and configuration for the system to work. You
need to provide the `addresses.json` file, which should be put in the directory
alongside the `docker-compose.yml` file.

This directory contains working example files for contracts already deployed on
the trustlines blockchain. If you deploy your own contracts, please adapt `addresses.json`
accordingly.

Let's first build and fetch all of the images that we will need without starting
any services with the following command:

```
docker-compose up --no-start
```

We need the compiled contracts, which are installed in the relay server image. Copy them with:
```
docker-compose run --rm --no-deps -v $(pwd):/here --entrypoint /bin/bash relay -c "cp /opt/relay/trustlines-contracts/build/contracts.json /here"
```

We need to start the index container for initial database setup:
```
docker-compose run --rm index /bin/bash
```

Please run the following commands:
```
ethindex createtables
cd /tmp; ethindex importabi
exit
```

After that the system can be started `docker-compose up -d`, though you have to
wait for the blockchain node to sync with the trustlines blockchain in order to have a fully
functioning system.
