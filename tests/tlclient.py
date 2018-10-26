#! /usr/bin/env python

"""this program is only meant for testing. it contains a very basic relay
server client."""

import requests


class Client:
    def __init__(self, host):
        self.host = host

    def post(self, path, data):
        return requests.post(self.host + path, json=data).json()

    def get(self, path):
        return requests.get(self.host + path).json()

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

    def user_events(self, network, user):
        return self.get(f"users/{user}/events")


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


if __name__ == "__main__":
    client = Client("http://localhost:5000/api/v1/")

    # run_all_close_trustline_path_info(client)
    show_all_user_events(client)
