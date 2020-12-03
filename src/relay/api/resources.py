import logging
import tempfile
import time

import wrapt
from flask import abort, make_response, request, send_file
from flask.views import MethodView
from flask_restful import Resource
from marshmallow import fields as marshmallow_fields, validate
from tldeploy import identity
from webargs import fields
from webargs.flaskparser import use_args

from relay.api import fields as custom_fields
from relay.blockchain.currency_network_events import (
    all_event_types as all_currency_network_event_types,
    trustline_event_types,
)
from relay.blockchain.delegate import (
    IdentityDeploymentFailedException,
    InvalidChainId,
    InvalidDelegationFeesException,
    InvalidIdentityContractException,
    InvalidMetaTransactionException,
    InvalidNonceHashPair,
    InvalidSignature,
    InvalidTimeLimit,
    UnknownIdentityFactoryException,
)
from relay.blockchain.exchange_events import all_event_types as all_exchange_event_types
from relay.blockchain.unw_eth_events import all_event_types as all_unw_eth_event_types
from relay.ethindex_db.events_informations import (
    EventNotFoundException,
    IdentifiedNotPartOfTransferException,
    TransferNotFoundException,
)
from relay.network_graph.payment_path import FeePayer, PaymentPath
from relay.relay import TrustlinesRelay, all_event_contract_types
from relay.utils import get_version, sha3

from .schemas import (
    AccruedInterestListSchema,
    AggregatedAccountSummarySchema,
    AnyEventSchema,
    AppliedDelegationFeeSchema,
    CurrencyNetworkEventSchema,
    CurrencyNetworkSchema,
    DebtsListInCurrencyNetworkSchema,
    IdentityInfosSchema,
    MediationFeesListSchema,
    MetaTransactionFeeSchema,
    MetaTransactionSchema,
    MetaTransactionStatusSchema,
    PaymentPathSchema,
    TransactionIdentifierSchema,
    TransactionStatusSchema,
    TransferIdentifierSchema,
    TransferInformationSchema,
    TransferredSumSchema,
    TrustlineSchema,
    TxInfosSchema,
    UserCurrencyNetworkEventSchema,
)

logger = logging.getLogger("api.resources")


def abort_if_unknown_network(trustlines, network_address):
    if not trustlines.is_currency_network(network_address):
        abort(404, "Unknown network: {}".format(network_address))


def abort_if_frozen_network(trustlines, network_address):
    if trustlines.is_currency_network_frozen(network_address):
        abort(400, "Frozen network: {}".format(network_address))


def abort_if_unknown_or_frozen_network(trustlines, network_address):
    abort_if_unknown_network(trustlines, network_address)
    abort_if_frozen_network(trustlines, network_address)


def dump_result_with_schema(schema):
    """returns a decorator that calls schema.dump on the functions or methods
    return value"""

    @wrapt.decorator
    def dump_result(wrapped, instance, args, kwargs):
        return schema.dump(wrapped(*args, **kwargs))

    return dump_result


def handle_meta_transaction_exceptions(function_to_call):
    def handle_exceptions(meta_transaction):
        try:
            return function_to_call(meta_transaction)
        except InvalidDelegationFeesException:
            abort(
                400,
                "Invalid delegation fees: fees too low, not supported currency network of fees, "
                "or invalid fee recipient",
            )
        except InvalidTimeLimit:
            abort(400, f"Invalid time limit for meta-tx: {meta_transaction.time_limit}")
        except identity.ValidateTimeLimitNotFound:
            abort(
                400,
                "The function to validate the time limit was not found in the contract",
            )
        except InvalidChainId:
            abort(400, f"Invalid chain id for meta-tx: {meta_transaction.chain_id}")
        except InvalidNonceHashPair:
            abort(
                400,
                f"Invalid (nonce, hash) pair for meta-tx: ({meta_transaction.nonce}, {meta_transaction.hash})",
            )
        except identity.ValidateNonceNotFound:
            abort(
                400,
                "The function to validate the nonce and hash was not found in the contract",
            )
        except InvalidSignature:
            abort(400, f"Invalid signature for meta-tx: {meta_transaction.signature}")
        except identity.ValidateSignatureNotFound:
            abort(
                400,
                "The function to validate the signature was not found in the contract",
            )
        except InvalidMetaTransactionException:
            abort(400, "The meta-transaction is invalid")
        except InvalidIdentityContractException as exception:
            abort(
                400,
                f"This meta transaction belongs to an invalid or unknown identity contract: {exception}",
            )

    return handle_exceptions


class Version(Resource):
    def get(self):
        return f"relay/v{get_version()}"


class NetworkList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(CurrencyNetworkSchema(many=True))
    def get(self):
        return self.trustlines.get_network_infos()


class Network(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(CurrencyNetworkSchema())
    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.get_network_info(network_address)


class UserList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.get_users_of_network(network_address)


class User(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(AggregatedAccountSummarySchema())
    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        return self.trustlines.currency_network_graphs[network_address].get_account_sum(
            user_address, timestamp=timestamp
        )


class ContactList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.get_friends_of_user_in_network(
            network_address, user_address
        )


def _id(network_address, a_address, b_address):
    if a_address < b_address:
        return sha3(network_address + a_address + b_address)
    else:
        return sha3(network_address + b_address + a_address)


def _get_extended_account_summary(
    graph, network_address, a_address, b_address, timestamp: int
):
    account_summary = graph.get_account_sum(a_address, b_address, timestamp=timestamp)
    account_summary.user = a_address
    account_summary.counterParty = b_address
    account_summary.id = _id(network_address, a_address, b_address)
    account_summary.currencyNetwork = network_address
    return account_summary


class Trustline(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TrustlineSchema())
    def get(self, network_address, a_address, b_address):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]
        return _get_extended_account_summary(
            graph, network_address, a_address, b_address, timestamp=timestamp
        )


class TrustlineList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TrustlineSchema(many=True))
    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]
        friends = graph.get_friends(user_address)
        return [
            _get_extended_account_summary(
                graph,
                network_address,
                user_address,
                friend_address,
                timestamp=timestamp,
            )
            for friend_address in friends
        ]


class UserTrustlines(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TrustlineSchema(many=True))
    def get(self, user_address: str):
        timestamp = int(time.time())
        trustline_list = []
        for network_address, graph in self.trustlines.currency_network_graphs.items():
            for friend_address in graph.get_friends(user_address):
                trustline_list.append(
                    _get_extended_account_summary(
                        graph,
                        network_address,
                        user_address,
                        friend_address,
                        timestamp=timestamp,
                    )
                )
        return trustline_list


class NetworkTrustlinesList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TrustlineSchema(many=True))
    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]
        all_trustlines = graph.get_trustlines_list()
        return [
            _get_extended_account_summary(
                graph, network_address, a, b, timestamp=timestamp
            )
            for (a, b) in all_trustlines
        ]


class MaxCapacityPath(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "maxHops": fields.Int(required=False, missing=None),
        "from": custom_fields.Address(required=True),
        "to": custom_fields.Address(required=True),
    }

    @use_args(args)
    def post(self, args, network_address: str):
        abort_if_unknown_or_frozen_network(self.trustlines, network_address)

        source = args["from"]
        target = args["to"]
        max_hops = args["maxHops"]

        timestamp = int(time.time())

        capacity, path = self.trustlines.currency_network_graphs[
            network_address
        ].find_maximum_capacity_path(
            source=source, target=target, max_hops=max_hops, timestamp=timestamp
        )

        return {"capacity": str(capacity), "path": path}


class UserEventsNetwork(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(all_currency_network_event_types),
            missing=None,
        ),
    }

    @use_args(args)
    @dump_result_with_schema(UserCurrencyNetworkEventSchema(many=True))
    def get(self, args, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args["fromBlock"]
        type = args["type"]

        return self.trustlines.get_user_network_events(
            network_address, user_address, type=type, from_block=from_block
        )


class TrustlineEvents(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(trustline_event_types),
            missing=None,
        ),
    }

    @use_args(args)
    @dump_result_with_schema(UserCurrencyNetworkEventSchema(many=True))
    def get(
        self, args, network_address: str, user_address: str, counter_party_address: str
    ):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args["fromBlock"]
        type = args["type"]

        return self.trustlines.get_trustline_events(
            network_address,
            user_address,
            counter_party_address,
            type=type,
            from_block=from_block,
        )


class UserEvents(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(
                all_currency_network_event_types
                + all_unw_eth_event_types
                + all_exchange_event_types
            ),
            missing=None,
        ),
        "contractType": fields.Str(
            required=False,
            missing=None,
            validate=validate.OneOf(all_event_contract_types),
        ),
    }

    @use_args(args)
    @dump_result_with_schema(AnyEventSchema(many=True))
    def get(self, args, user_address: str):
        type = args["type"]
        from_block = args["fromBlock"]
        contract_type = args["contractType"]

        return self.trustlines.get_user_events(
            user_address,
            event_type=type,
            from_block=from_block,
            contract_type=contract_type,
        )


class EventsNetwork(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(all_currency_network_event_types),
            missing=None,
        ),
    }

    @use_args(args)
    @dump_result_with_schema(CurrencyNetworkEventSchema(many=True))
    def get(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args["fromBlock"]
        type = args["type"]

        return self.trustlines.get_network_events(
            network_address, type=type, from_block=from_block
        )


class UserAccruedInterestList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "startTime": fields.Int(required=False, missing=0),
        "endTime": fields.Int(required=False, missing=None),
    }

    @use_args(args)
    @dump_result_with_schema(AccruedInterestListSchema(many=True))
    def get(self, args, network_address: str, user_address):
        abort_if_unknown_network(self.trustlines, network_address)
        start_time = args["startTime"]
        end_time = args["endTime"]

        accrued_interest_list = []

        for friend in self.trustlines.get_friends_of_user_in_network(
            network_address, user_address
        ):
            accrued_interest_with_friend = self.trustlines.get_list_of_accrued_interests_for_trustline(
                network_address, user_address, friend, start_time, end_time
            )
            if len(accrued_interest_with_friend) != 0:
                accrued_interest_list.append(
                    {
                        "accruedInterests": accrued_interest_with_friend,
                        "user": user_address,
                        "counterparty": friend,
                    }
                )
        return accrued_interest_list


class TrustlineAccruedInterestList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "startTime": fields.Int(required=False, missing=0),
        "endTime": fields.Int(required=False, missing=None),
    }

    @use_args(args)
    @dump_result_with_schema(AccruedInterestListSchema())
    def get(self, args, network_address: str, user_address, counterparty_address):
        abort_if_unknown_network(self.trustlines, network_address)
        start_time = args["startTime"]
        end_time = args["endTime"]

        accrued_interests = self.trustlines.get_list_of_accrued_interests_for_trustline(
            network_address, user_address, counterparty_address, start_time, end_time
        )
        return {
            "accruedInterests": accrued_interests,
            "user": user_address,
            "counterparty": counterparty_address,
        }


class UserEarnedMediationFeesList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "startTime": fields.Int(required=False, missing=0),
        "endTime": fields.Int(required=False, missing=None),
    }

    @use_args(args)
    @dump_result_with_schema(MediationFeesListSchema())
    def get(self, args, network_address: str, user_address):
        abort_if_unknown_network(self.trustlines, network_address)
        start_time = args["startTime"]
        end_time = args["endTime"]
        mediationFees = self.trustlines.get_earned_mediation_fees(
            network_address, user_address, start_time, end_time
        )

        return {
            "mediationFees": mediationFees,
            "user": user_address,
            "network": network_address,
        }


class UserDebtsLists(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(DebtsListInCurrencyNetworkSchema(many=True))
    def get(self, user_address):
        return self.trustlines.get_debt_list_of_user(user_address)


class TotalTransferredSum(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "startTime": fields.Int(required=False, missing=0),
        "endTime": fields.Int(required=False, missing=None),
    }

    @use_args(args)
    @dump_result_with_schema(TransferredSumSchema())
    def get(self, args, network_address: str, sender_address, receiver_address):
        abort_if_unknown_network(self.trustlines, network_address)
        start_time = args["startTime"]
        end_time = args["endTime"]

        if end_time is None:
            end_time = time.time()

        value = self.trustlines.get_total_sum_transferred(
            network_address, sender_address, receiver_address, start_time, end_time
        )
        return {
            "sender": sender_address,
            "receiver": receiver_address,
            "startTime": start_time,
            "endTime": end_time,
            "value": value,
        }


class TransferInformation(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @use_args(TransferIdentifierSchema())
    @dump_result_with_schema(TransferInformationSchema(many=True))
    def get(self, args):
        transaction_hash = args["transactionHash"]
        block_hash = args["blockHash"]
        log_index = args["logIndex"]

        if transaction_hash is not None:
            try:
                return self.trustlines.get_transfer_information_for_tx_hash(
                    transaction_hash
                )
            except TransferNotFoundException as e:
                abort(
                    404,
                    f"No transfer found in transaction with transaction hash: {e.tx_hash}",
                )
        elif block_hash is not None and log_index is not None:
            try:
                return self.trustlines.get_transfer_information_from_event_id(
                    block_hash, log_index
                )
            except EventNotFoundException as e:
                abort(
                    404,
                    f"No event found in block {e.block_hash} with log index: {e.log_index}",
                )
            except IdentifiedNotPartOfTransferException as e:
                abort(
                    400,
                    f"The event identified by block hash {e.block_hash} and log index {e.log_index} "
                    "is not part of a Transfer",
                )
        else:
            raise RuntimeError("Unhandled input parameters.")


class AppliedDelegationFees(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @use_args(TransactionIdentifierSchema())
    @dump_result_with_schema(AppliedDelegationFeeSchema(many=True))
    def get(self, args):
        transaction_hash = args["transactionHash"]

        return self.trustlines.get_paid_delegation_fees_for_tx_hash(transaction_hash)


class TransactionInfos(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TxInfosSchema())
    def get(self, user_address: str):
        return self.trustlines.node.get_tx_infos(user_address)


class Relay(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {"rawTransaction": fields.String(required=True)}

    @use_args(args)
    def post(self, args):
        try:
            return self.trustlines.node.relay_tx(args["rawTransaction"]).hex()
        except ValueError:  # should mean error in relaying the transaction
            abort(409, "There was an error while relaying this transaction")


class TransactionStatus(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TransactionStatusSchema())
    def get(self, transaction_hash):
        return {"status": self.trustlines.node.get_transaction_status(transaction_hash)}


class RelayMetaTransaction(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "metaTransaction": marshmallow_fields.Nested(
            MetaTransactionSchema, required=True
        )
    }

    @use_args(args)
    def post(self, args):
        meta_transaction: identity.MetaTransaction = args["metaTransaction"]
        try:
            relay_meta_tx = handle_meta_transaction_exceptions(
                self.trustlines.delegate_meta_transaction
            )
            return relay_meta_tx(meta_transaction).hex()
        except ValueError:
            abort(409, "There was an error while relaying this meta-transaction")


class Status(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(MetaTransactionStatusSchema())
    def get(self, identity_address: str, meta_transaction_hash):
        return {
            "status": self.trustlines.get_meta_transaction_status(
                identity_address, meta_transaction_hash
            )
        }


class MetaTransactionFees(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "metaTransaction": marshmallow_fields.Nested(
            MetaTransactionSchema, required=True
        )
    }

    @use_args(args)
    @dump_result_with_schema(MetaTransactionFeeSchema(many=True))
    def post(self, args):
        meta_transaction: identity.MetaTransaction = args["metaTransaction"]
        get_meta_tx_fees = handle_meta_transaction_exceptions(
            self.trustlines.meta_transaction_fees
        )
        return get_meta_tx_fees(meta_transaction)


class Balance(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, user_address: str):
        return str(self.trustlines.node.balance(user_address))


class Block(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.node.blocknumber


class RequestEther(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def post(self):
        address = request.json["address"]
        return self.trustlines.node.send_ether(address)


class DeployIdentity(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "factoryAddress": custom_fields.Address(required=True),
        "implementationAddress": custom_fields.Address(required=True),
        "signature": custom_fields.HexEncodedBytes(required=True),
    }

    @use_args(args)
    @dump_result_with_schema(IdentityInfosSchema())
    def post(self, args):
        implementation_address = args["implementationAddress"]
        factory_address = args["factoryAddress"]
        signature = args["signature"]
        try:
            identity_contract_address = self.trustlines.deploy_identity(
                factory_address, implementation_address, signature
            )
        except UnknownIdentityFactoryException as exception:
            abort(
                400,
                f"The identity deployment was rejected, unknown factory: {exception.args}",
            )
        except IdentityDeploymentFailedException:
            abort(400, "The identity deployment failed, identity already deployed?")
        try:
            return self.trustlines.get_identity_info(identity_contract_address)
        except InvalidIdentityContractException:
            abort(400, "The deployed identity is invalid.")


class IdentityInfos(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(IdentityInfosSchema())
    def get(self, identity_address: str):
        try:
            return self.trustlines.get_identity_info(identity_address)
        except InvalidIdentityContractException:
            abort(404, "Identity Contract not found or invalid")


class Factories(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.known_identity_factories


class Path(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "value": fields.Int(required=False, missing=1, validate=validate.Range(min=1)),
        "maxHops": fields.Int(required=False, missing=None),
        "maxFees": fields.Int(required=False, missing=None),
        "from": custom_fields.Address(required=True),
        "to": custom_fields.Address(required=True),
        "feePayer": custom_fields.FeePayerField(require=False, missing="sender"),
    }

    @use_args(args)
    @dump_result_with_schema(PaymentPathSchema())
    def post(self, args, network_address: str):
        abort_if_unknown_or_frozen_network(self.trustlines, network_address)
        timestamp = int(time.time())

        source = args["from"]
        target = args["to"]
        value = args["value"]
        max_fees = args["maxFees"]
        max_hops = args["maxHops"]
        fee_payer = FeePayer(args["feePayer"])

        if fee_payer == FeePayer.SENDER:
            cost, path = self.trustlines.currency_network_graphs[
                network_address
            ].find_transfer_path_sender_pays_fees(
                source=source,
                target=target,
                value=value,
                max_fees=max_fees,
                max_hops=max_hops,
                timestamp=timestamp,
            )
        elif fee_payer == FeePayer.RECEIVER:
            cost, path = self.trustlines.currency_network_graphs[
                network_address
            ].find_transfer_path_receiver_pays_fees(
                source=source,
                target=target,
                value=value,
                max_fees=max_fees,
                max_hops=max_hops,
                timestamp=timestamp,
            )
        else:
            raise ValueError(
                f"feePayer has to be one of {[fee_payer.name for fee_payer in FeePayer]}: {fee_payer}"
            )

        return PaymentPath(cost, path, value, fee_payer=fee_payer)


# CloseTrustline is similar to the above ReduceDebtPath, though it does not
# take `via` and `value` as parameters. Instead it tries to reduce the debt to
# zero and uses any contact to do so.


class CloseTrustline(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "maxHops": fields.Int(required=False, missing=None),
        "maxFees": fields.Int(required=False, missing=None),
        "from": custom_fields.Address(required=True),
        "to": custom_fields.Address(required=True),
    }

    @use_args(args)
    @dump_result_with_schema(PaymentPathSchema())
    def post(self, args, network_address: str):
        abort_if_unknown_or_frozen_network(self.trustlines, network_address)
        source = args["from"]
        target = args["to"]
        max_fees = args["maxFees"]
        max_hops = args["maxHops"]

        now = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]

        payment_path = graph.close_trustline_path_triangulation(
            timestamp=now,
            source=source,
            target=target,
            max_hops=max_hops,
            max_fees=max_fees,
        )

        return payment_path


class GraphImage(MethodView):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        filename = tempfile.mktemp(".gif")
        self.trustlines.currency_network_graphs[network_address].draw(filename)
        return send_file(filename, mimetype="image/gif")


class GraphDump(MethodView):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        response = make_response(
            self.trustlines.currency_network_graphs[network_address].dump()
        )
        cd = "attachment; filename=networkdump.csv"
        response.headers["Content-Disposition"] = cd
        response.mimetype = "text/csv"
        return response
