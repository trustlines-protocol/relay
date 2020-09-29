import json
import os
import subprocess
import sys
import time
import warnings
from subprocess import Popen

import pytest


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
    def is_started(self):
        return self.start_time is not None

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


def assert_within_timeout(check_function, timeout, poll_period=0.5):
    """
    Runs a check_function with assertions and give it some time to pass
    :param check_function: The function which will be periodically called. It should contain some assertions
    :param timeout: After this timeout non passing assertion will be raised
    :param poll_period: poll interval to check the check_function
    """
    with Timer(timeout) as timer:
        while True:
            try:
                check_function()
            except AssertionError as e:
                if not timer.is_timed_out():
                    time.sleep(min(poll_period, timer.time_left))
                else:
                    raise TimeoutException(
                        f"Assertion did not pass after {timeout} seconds. See causing exception for more details."
                    ) from e
            else:
                break


def assert_after_timout(check_function, timeout):
    time.sleep(timeout)
    check_function()


class Service:
    def __init__(
        self,
        args,
        *,
        name=None,
        env=None,
        timeout=5,
        poll_interval=0.2,
        process_settings=None,
    ):
        self.args = args
        self.name = name
        self.env = env
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.process = None
        self._process_settings = process_settings

        if self._process_settings is None:
            self._process_settings = {}

    def start(self):
        """Starts the service and wait for it to be up """
        if self.process:
            raise ServiceAlreadyStarted
        self.process = Popen(self.args, env=self.env, **self._process_settings)
        try:
            self._wait_for_up()
            return self.process
        except TimeoutException:
            self.terminate()
            raise

    def is_up(self):
        """Determine if the service is up"""
        return True

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


class PostgresDatabase(Service):
    def __init__(self, *, name=None):

        super().__init__(
            ["docker-compose", "up", "postgress"], name=name,
        )

    def is_up(self):
        return True


@pytest.fixture(scope="session")
def environment_variables():
    env = {
        **os.environ,
        "POSTGRES_USER": "trustlines_test",
        "POSTGRES_PASSWORD": "test123",
        "PGHOST": "127.0.0.1",
        "PGDATABASE": "trustlines_test",
        "PGUSER": "trustlines_test",
        "PGPASSWORD": "test123",
        "LC_ALL": "C.UTF-8",  # to make click work with subprocess / Popen
        "LANG": "C.UTF-8",  # to make click work with subprocess / Popen
    }
    return env


@pytest.fixture(scope="session")
def postgres_database(environment_variables):

    path_to_docker_compose = os.path.join(
        os.getcwd(), "tests/chain_integration/database_integration/docker-compose.yml"
    )

    process = Popen(
        ["docker-compose", "-f", path_to_docker_compose, "up", "postgres"],
        env=environment_variables,
    )
    time.sleep(3)

    yield process

    process = Popen(
        ["docker-compose", "-f", path_to_docker_compose, "down"],
        env=environment_variables,
    )


@pytest.fixture()
def address_file_path(testnetwork2_address):
    with open("addresses.json", "w") as f:
        json.dump({"networks": [testnetwork2_address]}, f)
    return "addresses.json"


@pytest.fixture(scope="session")
def abi_file_path():
    return os.path.join(sys.prefix, "trustlines-contracts", "build", "contracts.json")


@pytest.fixture(autouse=True)
def start_indexer(
    postgres_database, environment_variables, address_file_path, abi_file_path
):
    createtables_process = Popen(
        ["ethindex", "createtables"], env=environment_variables
    )
    all_processes = [createtables_process]

    time.sleep(5)

    import_abi_process = Popen(
        [
            "ethindex",
            "importabi",
            "--contracts",
            abi_file_path,
            "--addresses",
            address_file_path,
        ],
        env=environment_variables,
    )
    all_processes.append(import_abi_process)

    time.sleep(5)

    runsync_process = Popen(
        [
            "ethindex",
            "runsync",
            "--jsonrpc",
            "http://localhost:8545",
            "--waittime",
            "200",
        ],
        env=environment_variables,
    )
    all_processes.append(runsync_process)

    yield

    for process in all_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            warnings.warn(
                "start_indexer did not terminate in time and had to be killed"
            )
            process.kill()
            process.wait(timeout=5)
