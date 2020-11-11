import logging
from typing import Dict, List, Union

import attr

logger = logging.getLogger("sync_updates")


@attr.s()
class TrustlineUpdateFeedUpdate:
    args: Dict = attr.ib()
    address: str = attr.ib()
    timestamp: int = attr.ib()

    @property
    def from_(self):
        return self.args.get("_creditor")

    @property
    def to(self):
        return self.args.get("_debtor")

    @property
    def creditline_given(self):
        return self.args.get("_creditlineGiven")

    @property
    def creditline_received(self):
        return self.args.get("_creditlineReceived")

    @property
    def interest_rate_given(self):
        return self.args.get("_interestRateGiven", 0)

    @property
    def interest_rate_received(self):
        return self.args.get("_interestRateReceived", 0)

    @property
    def is_frozen(self):
        return self.args.get("_isFrozen")


@attr.s()
class BalanceUpdateFeedUpdate:
    args: Dict = attr.ib()
    address: str = attr.ib()
    timestamp: int = attr.ib()

    @property
    def value(self):
        return self.args.get("_value")

    @property
    def from_(self):
        return self.args.get("_from")

    @property
    def to(self):
        return self.args.get("_to")


def get_graph_updates_feed(
    conn,
) -> List[Union[TrustlineUpdateFeedUpdate, BalanceUpdateFeedUpdate]]:
    """Get a list of updates to be applied on the trustlines graphs to make them up to date with the chain"""

    query_string = """
        WITH deleted as (DELETE FROM graphfeed * RETURNING *)
        SELECT * FROM deleted ORDER BY id ASC;
    """

    with conn:
        with conn.cursor() as cur:
            cur.execute(query_string)
            rows = cur.fetchall()

    feed_update: List[Union[TrustlineUpdateFeedUpdate, BalanceUpdateFeedUpdate]] = []

    for row in rows:
        event_type = row.get("eventname", None)
        if event_type == "TrustlineUpdate":
            feed_update.append(
                TrustlineUpdateFeedUpdate(
                    args=row["args"], address=row["address"], timestamp=row["timestamp"]
                )
            )
        elif event_type == "BalanceUpdate":
            feed_update.append(
                BalanceUpdateFeedUpdate(
                    args=row["args"], address=row["address"], timestamp=row["timestamp"]
                )
            )
        else:
            logger.warning(f"Got feed update with unknown type from database: {row}")

    return feed_update
