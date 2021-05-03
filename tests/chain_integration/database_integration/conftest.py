import json
import os
import subprocess
import time
import warnings
from subprocess import Popen

import psycopg2
import pytest
from deploy_tools.plugin import EXPOSE_RPC_OPTION
from tests.conftest import LOCAL_DATABASE_OPTION

from relay.blockchain import currency_network_events
from relay.ethindex_db import ethindex_db
from relay.relay import ContractTypes, all_event_builders

"""
The tests are running a postgres database and ethindex to tests out getting and processing event information.
They assume that you can run docker and docker-compose.
Otherwise, you can run the tests with `--local-db` option and have a local postgres environment with:
- user: POSTGRES_USER
- password: POSTGRES_PASSWORD
- database: POSTGRES_DATABASE
- accessible on localhost:postgres_port
See tests/chain_integration/database_integration/conftest.py for actual values
"""


INDEXER_REQUIRED_CONFIRMATION = 50
POSTGRES_USER = "trustlines_test"
POSTGRES_PASSWORD = "test123"
POSTGRES_DATABASE = "trustlines_test"


class TimeoutException(Exception):
    pass


class ServiceAlreadyStarted(Exception):
    pass


class Timer:
    def __init__(self, timeout):
        self.start_time = None
        self.timeout = timeout

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def start(self):
        self.start_time = time.time()

    def is_timed_out(self):
        if self.start_time is None:
            raise ValueError("Timer is not started yet")
        return self.time_passed > self.timeout

    @property
    def time_left(self):
        if self.start_time is None:
            raise ValueError("Timer is not started yet")
        return self.timeout - self.time_passed

    @property
    def time_passed(self):
        if self.start_time is None:
            raise ValueError("Timer is not started yet")
        return time.time() - self.start_time


class PostgresDatabase:
    def __init__(
        self,
        environment_variables,
        *,
        timeout=10,
        poll_interval=0.2,
        process_settings=None,
    ):

        self.path_to_docker_compose = os.path.join(
            os.getcwd(),
            "tests/chain_integration/database_integration/docker-compose.yml",
        )
        self.environment_variables = environment_variables

        self.args = [
            "docker-compose",
            "-f",
            self.path_to_docker_compose,
            "up",
            "postgres",
        ]
        self.name = "Postgres database"
        self.env = environment_variables
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.process = None
        self._process_settings = process_settings

        if self._process_settings is None:
            self._process_settings = {}

    def start(self):
        """Starts the postgres database and wait for it to be up"""
        if is_port_in_use(self.environment_variables["PGPORT"]):
            raise EnvironmentError(
                f"The port {self.environment_variables['PGPORT']} "
                f"to be used by the database is already in use on the machine."
            )
        if self.process:
            raise ServiceAlreadyStarted

        self.process = Popen(
            self.args,
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **self._process_settings,
        )
        try:
            self._wait_for_up()
            return self.process
        except TimeoutException:
            self.terminate()
            raise

    def _wait_for_up(self):
        with Timer(self.timeout) as timer:
            while True:
                is_up = self.is_up()

                if not is_up:
                    if timer.is_timed_out():
                        raise TimeoutException(
                            f"Service {self.name} did not report to be up after {self.timeout} seconds"
                        )
                    else:
                        time.sleep(min(self.poll_interval, timer.time_left))
                else:
                    break

    def is_up(self):
        try:
            subprocess.run(
                [
                    "pg_isready",
                    "-d",
                    POSTGRES_DATABASE,
                    "-h",
                    "127.0.0.1",
                    "-p",
                    f"{self.environment_variables['PGPORT']}",
                    "-U",
                    POSTGRES_USER,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def terminate(self):
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            warnings.warn(f"{self.name} did not terminate in time and had to be killed")
            self.process.kill()
            self.process.wait(timeout=5)
        self.process = None
        Popen(
            ["docker-compose", "-f", self.path_to_docker_compose, "down"],
            env=self.environment_variables,
        )


def is_port_in_use(port):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", int(port))) == 0


@pytest.fixture(scope="session")
def use_local_database(pytestconfig):
    return pytestconfig.getoption(LOCAL_DATABASE_OPTION)


@pytest.fixture(scope="session")
def postgres_port(use_local_database):
    if use_local_database:
        return 5432
    else:
        return 5434


@pytest.fixture(scope="session")
def environment_variables(postgres_port):
    env = {
        **os.environ,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
        "PGHOST": "127.0.0.1",
        "PGPORT": f"{postgres_port}",
        "PGDATABASE": POSTGRES_DATABASE,
        "PGUSER": POSTGRES_USER,
        "PGPASSWORD": POSTGRES_PASSWORD,
        "LC_ALL": "C.UTF-8",  # to make click work with subprocess / Popen
        "LANG": "C.UTF-8",  # to make click work with subprocess / Popen
    }
    return env


@pytest.fixture(scope="session")
def address_file_path(
    tmp_path_factory,
    currency_network_with_trustlines_and_interests_session,
    currency_network_with_trustlines_session,
    currency_network,
    test_currency_network_v1,
):
    tmp_path_factory.mktemp("tmp_test_dir")
    path = os.path.join(tmp_path_factory.getbasetemp(), "addresses.json")
    with open(path, "w") as f:
        json.dump(
            {
                "networks": [
                    currency_network_with_trustlines_and_interests_session.address,
                    currency_network_with_trustlines_session.address,
                    currency_network.address,
                    test_currency_network_v1.address,
                ]
            },
            f,
        )
    return path


@pytest.fixture(scope="session", autouse=True)
def setup_database(use_local_database, environment_variables):
    if use_local_database:
        yield
    else:
        database = PostgresDatabase(environment_variables)
        database.start()

        yield database

        database.terminate()


@pytest.fixture(scope="session", autouse=True)
def start_indexer(
    pytestconfig, setup_database, environment_variables, address_file_path,
):
    subprocess.run(
        ["ethindex", "createtables"],
        env=environment_variables,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    subprocess.run(
        ["ethindex", "importabi", "--addresses", address_file_path],
        env=environment_variables,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    exposed_port = pytestconfig.getoption(EXPOSE_RPC_OPTION)
    runsync_process = Popen(
        [
            "ethindex",
            "runsync",
            "--jsonrpc",
            f"http://localhost:{exposed_port}",
            "--waittime",
            "100",
            "--required-confirmations",
            f"{INDEXER_REQUIRED_CONFIRMATION}",
        ],
        env=environment_variables,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    yield

    try:
        runsync_process.terminate()
        runsync_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        warnings.warn("runsync_process did not terminate in time and had to be killed")
        runsync_process.kill()
        runsync_process.wait(timeout=5)

    subprocess.run(
        ["ethindex", "droptables", "--force"],
        env=environment_variables,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


@pytest.fixture()
def replace_blocks_with_empty_from_snapshot(web3, chain):
    def revert(snapshot):
        last_block_number = web3.eth.blockNumber
        chain.revert_to_snapshot(snapshot)
        reverted_blocks = last_block_number - web3.eth.blockNumber
        # We need to mine one more block to make sure we correctly wait for ethindex to sync
        # by checking the number of the latest block.
        chain.mine_blocks(reverted_blocks + 1)
        assert (
            INDEXER_REQUIRED_CONFIRMATION > reverted_blocks
        ), "The reverted chain was final and events cannot be deleted."
        return chain.take_snapshot()

    return revert


@pytest.fixture(autouse=True)
def chain_cleanup(
    chain, web3, wait_for_ethindex_to_sync, replace_blocks_with_empty_from_snapshot
):
    """Cleans up the chain by replacing blocks with empty blocks, and giving time for the indexer to clean up."""
    # We mine blocks because the indexer will not remove the events of blocks if it does not receive replacing blocks
    snapshot = chain.take_snapshot()
    yield
    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()


@pytest.fixture()
def generic_db_connection(postgres_port):
    conn = psycopg2.connect(
        cursor_factory=psycopg2.extras.RealDictCursor,
        database=POSTGRES_DATABASE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host="127.0.0.1",
        port=postgres_port,
    )
    yield conn
    conn.commit()
    conn.close()


@pytest.fixture()
def wait_for_ethindex_to_sync(generic_db_connection, web3):
    def wait_for_sync(timeout=20, poll_interval=0.2):
        latest_block = web3.eth.getBlock("latest")["number"]
        with Timer(timeout) as timer:
            while True:
                try:
                    is_synced = (
                        ethindex_db.get_latest_ethindex_block_number(
                            generic_db_connection
                        )
                        == latest_block
                    )
                except RuntimeError:
                    # if ethindex_db did not even start syncing yet, we'll receive RuntimeError
                    is_synced = False

                if not is_synced:
                    if timer.is_timed_out():
                        raise TimeoutException(
                            f"EthindexDB is not synced after {timeout} seconds"
                        )
                    else:
                        time.sleep(min(poll_interval, timer.time_left))
                else:
                    break

    return wait_for_sync


@pytest.fixture()
def ethindex_db_for_currency_network(currency_network, generic_db_connection):
    return make_ethindex_db(currency_network.address, generic_db_connection)


@pytest.fixture()
def ethindex_db_for_currency_network_with_trustlines(
    currency_network_with_trustlines_session, generic_db_connection
):
    return make_ethindex_db(
        currency_network_with_trustlines_session.address, generic_db_connection
    )


@pytest.fixture()
def ethindex_db_for_currency_network_with_trustlines_and_interests(
    currency_network_with_trustlines_and_interests_session, generic_db_connection
):
    return make_ethindex_db(
        currency_network_with_trustlines_and_interests_session.address,
        generic_db_connection,
    )


def make_ethindex_db(network_address, conn):
    return ethindex_db.CurrencyNetworkEthindexDB(
        conn,
        address=network_address,
        standard_event_types=currency_network_events.standard_event_types,
        event_builders=all_event_builders,
        from_to_types=currency_network_events.from_to_types,
        address_to_contract_types={
            network_address: ContractTypes.CURRENCY_NETWORK.value
        },
    )
