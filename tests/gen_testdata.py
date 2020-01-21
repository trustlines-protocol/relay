#! /usr/bin/env python3
"""generate test data from TestCurrencyNetwork contract.

The TestCurrencyNetwork contract can be deployed with:

    tl-deploy test --currency-network-contract-name=TestCurrencyNetwork
"""
import abc
import itertools
import json
import os
import random
import sys

import click
import eth_utils
import tldeploy.core
from deploy_tools.deploy import wait_for_successful_transaction_receipt
from web3 import Web3


class TestDataGenerator(metaclass=abc.ABCMeta):
    def __init__(self, web3, contract):
        self.web3 = web3
        self.contract = contract

    @classmethod
    def name(cls):
        return cls.__name__

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
            sys.stdout.write(".")
            sys.stdout.flush()
        sys.stdout.write("\n")
        return dict(name=self.name(), data=result)


class CalculateFee(TestDataGenerator):
    def generate_input_data(self):
        prng = random.Random("666")
        for capacity_imbalance_fee_divisor in [2, 10, 50, 101, 1000]:
            for imbalance_generated in itertools.chain(
                [0, 10, 100], (prng.randint(0, 10000) for _ in range(40))
            ):
                yield dict(
                    imbalance_generated=imbalance_generated,
                    capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
                )

    def compute_one_result(self, imbalance_generated, capacity_imbalance_fee_divisor):
        return dict(
            fees=self.contract.functions.testCalculateFees(
                imbalance_generated, capacity_imbalance_fee_divisor
            ).call(),
            fees_reverse=self.contract.functions.testCalculateFeesReverse(
                imbalance_generated, capacity_imbalance_fee_divisor
            ).call(),
        )


class ImbalanceGenerated(TestDataGenerator):
    MAX_BALANCE = 2 ** 71 - 1
    MIN_BALANCE = -MAX_BALANCE

    balances = (
        MIN_BALANCE,
        MIN_BALANCE + 100,
        -1000,
        -100,
        0,
        100,
        1000,
        MAX_BALANCE - 100,
        MAX_BALANCE,
    )
    values = (0, 1, 10, 100, 1000, 2 ** 64 - 1)

    def generate_input_data(self):
        for balance in self.balances:
            for value in self.values:
                yield dict(value=value, balance=balance)

    def compute_one_result(self, value, balance):
        return dict(
            imbalance_generated=self.contract.functions.testImbalanceGenerated(
                value, balance
            ).call()
        )


class Transfer(TestDataGenerator):
    def _gen_addresses(self, num_addresses):
        return [
            eth_utils.to_checksum_address(f"0x{address:040d}")
            for address in range(1, num_addresses + 1)
        ]

    def generate_input_data(self):
        return itertools.chain(
            self._generate_input_data0(), self._generate_input_data1()
        )

    def _generate_input_data1(self):
        # generate input data by modifying part of the other generator
        prng = random.Random("666")
        for testdata in self._generate_input_data0():
            num_balances = len(testdata["balances_before"])
            if num_balances != 4:  # keep test set small
                continue
            balances_before = [
                prng.choice([0, 1000, -1000, 10000, -10000, 100_000, -100_000])
                for _ in range(num_balances)
            ]
            testdata["balances_before"] = balances_before
            yield testdata

    def _generate_input_data0(self):
        for num_hops in range(1, 6):
            addresses = self._gen_addresses(num_hops + 1)
            balances_before = [0] * num_hops
            assert len(addresses) - 1 == num_hops
            for fees_paid_by in ["sender", "receiver"]:
                for capacity_imbalance_fee_divisor in [10, 100, 1000]:
                    for value in [1000, 10000, 1_000_000]:
                        yield dict(
                            fees_paid_by=fees_paid_by,
                            value=value,
                            capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
                            addresses=addresses,
                            balances_before=balances_before,
                        )

    def compute_one_result(
        self,
        fees_paid_by,
        value,
        capacity_imbalance_fee_divisor,
        addresses,
        balances_before,
    ):
        self.contract.functions.setCapacityImbalanceFeeDivisor(
            capacity_imbalance_fee_divisor
        ).transact()

        for a, b, balance in zip(addresses, addresses[1:], balances_before):
            txid = self.contract.functions.setAccount(
                a, b, 100_000_000, 100_000_000, 0, 0, False, 0, balance
            ).transact()

        # we only wait for the last transaction to speed things up
        wait_for_successful_transaction_receipt(self.contract.web3, txid)

        assert fees_paid_by in ("sender", "receiver")
        if fees_paid_by == "sender":
            fn = self.contract.functions.testTransferSenderPays
        elif fees_paid_by == "receiver":
            fn = self.contract.functions.testTransferReceiverPays
        txid = fn(value, value, addresses).transact()
        wait_for_successful_transaction_receipt(self.contract.web3, txid)
        balances = [
            self.contract.functions.getAccount(a, b).call()[-1]
            for a, b in zip(addresses, addresses[1:])
        ]

        return dict(balances_after=balances)


def generate_and_write_testdata(generator_class, web3, contract, output_directory):
    generator = generator_class(web3, contract)
    print(f"generating testdata with generator {generator.name()}")
    testdata = generator.make_test_data()
    filename = os.path.join(output_directory, f"{generator.name()}.json")
    print(f"writing testdata to {filename}")
    with open(filename, "w") as outfile:
        json.dump(testdata, outfile, indent=4, sort_keys=True)
        outfile.write("\n")


@click.command()
@click.option(
    "--output-directory",
    help="directory where json files are written",
    default="testdata",
)
@click.option(
    "--url", help="URL of address of contract", default="http://localhost:8545"
)
@click.argument("generator_names", nargs=-1)
def main(url, output_directory, generator_names):
    if not os.path.isdir(output_directory):
        click.echo(
            """Error: The output directory has not been found. Please specify it with --output-directory
or cd into the tests directory."""
        )
        sys.exit(1)
    web3 = Web3(Web3.HTTPProvider(url))

    def make_contract():
        return tldeploy.core.deploy_network(
            web3=web3,
            name="TestNet",
            symbol="E",
            decimals=4,
            fee_divisor=100,
            currency_network_contract_name="TestCurrencyNetwork",
            expiration_time=2_000_000_000,
        )

    name2cls = {cls.name(): cls for cls in (CalculateFee, ImbalanceGenerated, Transfer)}
    if not generator_names:
        generator_names = list(name2cls.keys())
    for generator_name in generator_names:
        cls = name2cls[generator_name]
        generate_and_write_testdata(
            cls, web3, make_contract(), output_directory=output_directory
        )


if __name__ == "__main__":
    main()
