#! /usr/bin/env python3
"""generate test data from TestCurrencyNetwork contract

The TestCurrencyNetwork contract can be deployed with:

    tl-deploy test --currency-network-contract-name=TestCurrencyNetwork


"""
import os
import sys
import json
import random
import abc

import click
from web3 import Web3


def load_contracts():
    """load the contracts.json file that is being installed with
    trustlines-contracts-bin"""
    with open(
        os.path.join(sys.prefix, "trustlines-contracts", "build", "contracts.json")
    ) as data_file:
        contracts = json.load(data_file)
        return contracts


def load_test_currency_network_abi():
    """load the TestCurrencyNetwork's ABI from the contracts.json file """
    return load_contracts()["TestCurrencyNetwork"]["abi"]


class TestDataGenerator(metaclass=abc.ABCMeta):
    def __init__(self, web3, contract):
        self.web3 = web3
        self.contract = contract

    @property
    def name(self):
        return self.__class__.__name__

    @abc.abstractmethod
    def generate_input_data(self):
        pass

    @abc.abstractmethod
    def compute_one_result(self, **kw):
        pass

    def make_test_data(self):
        result = []
        for input_data in self.generate_input_data():
            result.append(
                dict(input_data=input_data, **self.compute_one_result(**input_data))
            )
        return dict(name=self.name, data=result)


class CalculateFeeGenerator(TestDataGenerator):
    def generate_input_data(self):
        def asdict(imbalance_generated, capacity_imbalance_fee_divisor):
            return dict(
                imbalance_generated=imbalance_generated,
                capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
            )

        prng = random.Random("666")
        for capacity_imbalance_fee_divisor in [2, 10, 50, 101, 1000]:
            yield asdict(0, capacity_imbalance_fee_divisor)
            yield asdict(10, capacity_imbalance_fee_divisor)
            yield asdict(100, capacity_imbalance_fee_divisor)
            for _ in range(40):
                imbalance_generated = prng.randint(0, 10000)
                yield asdict(imbalance_generated, capacity_imbalance_fee_divisor)

    def compute_one_result(self, imbalance_generated, capacity_imbalance_fee_divisor):
        return dict(
            calculateFees=self.contract.functions.testCalculateFees(
                imbalance_generated, capacity_imbalance_fee_divisor
            ).call(),
            calculateFeesReverse=self.contract.functions.testCalculateFeesReverse(
                imbalance_generated, capacity_imbalance_fee_divisor
            ).call(),
        )


def generate_and_write_testdata(generator_class, web3, contract):
    generator = generator_class(web3, contract)
    print(f"generating testdata with generator {generator.name}")
    testdata = generator.make_test_data()
    filename = f"testdata/{generator.name}.json"
    print(f"writing testdata to {filename}")
    with open(filename, "w") as outfile:
        json.dump(testdata, outfile, indent=4, sort_keys=True)
        outfile.write("\n")


@click.command()
@click.option('--address', help='address of contract', required=True)
@click.option('--url', help='URL of address of contract', default="http://localhost:8545")
def main(address, url):
    web3 = Web3(Web3.HTTPProvider(url))
    abi = load_test_currency_network_abi()
    contract = web3.eth.contract(abi=abi, address=address)
    generate_and_write_testdata(CalculateFeeGenerator, web3, contract)


if __name__ == "__main__":
    main()
