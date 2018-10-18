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


def run_all_close_trustline_path_info():
    """try to run close_trustline_path_info on all combinations"""
    c = Client("http://localhost:5000/api/v1/")
    all_networks = c.networks()
    for network_info in all_networks:
        print("=====> Using network", network_info)
        network_address = network_info["address"]

        users = c.users(network_address)
        print(f"have {len(users)} users")
        for user in users:
            trustlines = c.trustlines(network_address, user)
            print(f"user {user} has {len(trustlines)} trustlines")
            for t in trustlines:
                res = c.close_trustline_path_info(
                    network_address, user, t["counterParty"]
                )
                if res.get("path"):
                    print(res, t)


if __name__ == "__main__":
    run_all_close_trustline_path_info()
