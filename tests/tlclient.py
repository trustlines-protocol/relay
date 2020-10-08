#! /usr/bin/env python

"""this program is only meant for testing. it contains a very basic relay
server client."""
import functools
import time
from typing import Any, List

import requests


class Client:
    def __init__(self, host):
        self.host = host

    def post(self, path, data):
        r = requests.post(self.host + path, json=data)
        r.raise_for_status()
        return r.json()

    def get(self, path, params=None):
        r = requests.get(self.build_url(path), params=params)
        r.raise_for_status()
        return r.json()

    def build_url(self, path):
        return self.host + path

    def networks(self):
        return self.get("networks")

    def users(self, network):
        return self.get(f"networks/{network}/users")

    def trustlines(self, network, user):
        return self.get(f"networks/{network}/users/{user}/trustlines")

    def close_trustline_path_info(self, network, user, other_user):
        return self.post(
            f"networks/{network}/close-trustline-path-info",
            {"from": user, "to": other_user},
        )

    def transfer_details(self, block_hash, log_index):
        details = self.get(
            "transfers", params={"blockHash": block_hash, "logIndex": log_index}
        )
        return details[0]

    def transfer_status(self, transaction_hash):
        status = self.get(f"transactions/{transaction_hash}/status")
        return status

    def transfers(self, network):
        return self.get(f"networks/{network}/events", params={"type": "Transfer"})

    def user_events(self, network, user):
        return self.get(f"users/{user}/events")


def time_it(fun):
    start = time.time()
    fun()
    return time.time() - start


def run_performance_test(calls, *, wait_between_calls=0.0):
    print("Start performance test")

    def run(call):
        dur = time_it(call)
        time.sleep(wait_between_calls)
        return dur

    durations = [run(call) for call in calls]

    print("Summary:")
    print(f"Max: {max(durations)}")
    print(f"Min: {min(durations)}")
    print(f"Avg: {sum(durations) / len(durations)}")


def run_all_close_trustline_path_info(client):
    """try to run close_trustline_path_info on all combinations"""
    all_networks = client.networks()
    for network_info in all_networks:
        print("=====> Using network", network_info)
        network_address = network_info["address"]

        users = client.users(network_address)
        print(f"have {len(users)} users")
        for user in users:
            trustlines = client.trustlines(network_address, user)
            print(f"user {user} has {len(trustlines)} trustlines")
            for t in trustlines:
                res = client.close_trustline_path_info(
                    network_address, user, t["counterParty"]
                )
                if res.get("path"):
                    print(res, t)


def show_all_user_events(client):
    all_networks = client.networks()
    for network_info in all_networks:
        print("=====> Using network", network_info)
        network_address = network_info["address"]

        users = client.users(network_address)
        print(f"have {len(users)} users")
        for user in users:
            events = client.user_events(network_address, user)
            print(user, network_address, events)


def performance_test_transfer_details(client: Client):
    networks = [network["address"] for network in client.networks()]
    print(f"Found {len(networks)} networks")

    transfers: List[Any] = []
    for network in networks:
        transfers.extend(client.transfers(network))

    print(f"Found {len(transfers)} transfers")

    calls = [
        functools.partial(
            client.transfer_details, transfer["blockHash"], transfer["logIndex"]
        )
        for transfer in transfers
    ]

    run_performance_test(calls)


def performance_test_transfer_status(client: Client):
    networks = [network["address"] for network in client.networks()]
    print(f"Found {len(networks)} networks")

    transfers: List[Any] = []
    for network in networks:
        transfers.extend(client.transfers(network))

    print(f"Found {len(transfers)} transfers")

    calls = [
        functools.partial(client.transfer_status, transfer["transactionHash"])
        for transfer in transfers
    ]

    # Wait between calls to not run into rate limit
    run_performance_test(calls, wait_between_calls=0.5)


if __name__ == "__main__":
    client = Client("https://staging.testnet.trustlines.network/api/v1/")

    # run_all_close_trustline_path_info(client)
    # show_all_user_events(client)
    performance_test_transfer_details(client)
