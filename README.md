# RELAY API

## Response Format
Response format is based on some best practices. (see https://github.com/adnan-kamili/rest-api-response-format)

## Base URL
`/api/v1`

## Error message
In case of an error, the response of the relay API will have the following format:
```javascript
{
    "error": "<errorMessage>"
}
```

## `TODO` Get all currency networks
Returns all registered currency networks with high-level information (similar to `GET tokens/`)

`GET /networks`

### Response
```javascript
[
    {
        "address": "0xabef1022e1ff..."
        "name": "Euro",
        "abbreviation": "EUR",
        "symbol": "€" // optional
    },
    ... // other currency networks
]
```
### Used Contract
Registry Contract

## `TODO` Get detailed information of currency network
Returns detailed information of currency network (similar to `GET tokens/:address`)

`GET /networks/:address`

### Response
```javascript
{
    "name": "Euro",
    "abbreviation": "EUR",
    "symbol": "€",
    "numUsers": "1000",
    ... // other information of currency network
}
```

## `TODO` Get users in currency network
Returns all addresses of users in currency network (similar to `GET tokens/:token_address/users`)

`GET /networks/:networkAddress/users`

### Response
```javascript
["0xabef1022e1ff...", "0xeef43fa1222b...", ...]
```

## `TODO` Get user information of currency network
Returns detailed information of currency network in user context (similar to `GET tokens/:token_address/users/:user_address`)

`GET /networks/:networkAddress/users/:userAddress`

### Response
```javascript
{
    "name": "Euro",
    "abbreviation": "EUR",
    "symbol": "€",
    "balance": "1000", // sum over balances of all trustlines user has in currency network
    "creditLinesGiven": "2000", // sum of all creditlines given by user in currency network
    "creditLinesReceived": "3000", // sum of all creditlines received by user in currency network
    "numTrustlines": 10 // amount of trustlines user has
}
```

## `TODO` Get contacts of user
Returns a list of addresses of all contacts of the user (similar to `GET tokens/:token_address/users/:user_address/friends`)

(doesn"t communicate with contracts)

`GET /networks/:networkAddress/users/:userAddress/contacts`

### Response
```javascript
["0xac33ffg3g...", "0xec33ffg3g...", ...]
```

## `TODO` Get all trustlines of user
Returns a list of trustlines a user has in a currency network (similar to `GET tokens/:token_address/users/:user_address/accounts`)

**PROBLEM: rounding decimal numbers in javascript (how does web3 do it?)**

`GET /networks/:networkAddress/users/:userAddress/trustlines`

### Response
```javascript
[
    {
        "addressB": "0xb33f5gaac...", // address of user B
        "balance": "100", // balance of trustline from POV of user A
        "given": "500", // credit line given by A
        "leftGiven": "400" // given - balance
        "received": "600", // credit line received from B
        "leftReceived": "700" // received + balance
        "interestRate": "0.1" // PROBLEM: rounding in js
    },
    ... // other trustlines
]
```

## `TODO` Get trustline to user
Return a trustline between A and B in a currency network if one exists. (similar to `GET tokens/:token_address/users/:a_address/accounts/:b_address`)

`GET /networks/:networkAddress/users/:userAddressA/trustlines/:userAddressB`

### Response
```javascript
{
    "balance": "100", // balance of trustline from POV of user A
    "given": "500", // credit line given by A
    "received": "600", // credit line received from B
    "interestRate": "0.1" // PROBLEM: rounding in js
}
```

## `NEW` Get total spendable amount
Returns amount a user can spend in a currency network.

`GET /networks/:networkAddress/users/:addressA/spendables`

```javascript
{
    "spendable": "1000"
}
```

### Parameters
- `ETH` - amount of money that should be transferred through path (optional)
- `maxHops` - specify maximal hops for path (optional)
- `maxFees` - specify maximal fees user is ready to pay (optional)

## `TODO` Get path
Returns the cheapest path and maximal sendable amount with calculated fees if existent (similar to `GET tokens/:token_address/users/:a_address/path/:b_address/value/:value`)

`GET /networks/:networkAddress/users/:aAddress/path/:bAddress?value=:value&maxHops=:maxHops&maxFees=:maxFees`

### Parameters
- `value` - amount of money that should be transferred through path (optional)
- `maxHops` - specify maximal hops for path (optional)
- `maxFees` - specify maximal fees user is ready to pay (optional)

### Response
```javascript
{
    "path": ["0xabc123bb...", "0xeebc3bb...", ...], // addresses of users in path
    "maxSpendable": "1200.12",
    "fees": "0.12" // fees for calculated path
}
```

## `TODO` Poll all events
Returns all events

`GET /networks/:networkAddress/users/:userAddress/events?type=:eventType&fromBlock=:fromBlock&toBlock=:toBlock`

### Parameters
- `type` - Type of event (i.e. `CreditLineUpdated`, `CreditLineAccepted`, `Transferred`)
- `fromBlock`- Start of range for events
- `toBlock` - End of range for events

### Response
```javascript
[
    {
        "blockNumber": 1,
        "event": Transfered(networkAddress, receiverAddress, amount, timestamp)
    },
    {
        "blockNumber": 2,
        "event": CreditLineRequested(networkAddress, receiverAddress, amount, timestamp)
    },
    ...
]
```

## Get transaction infos
Returns the transaction information

`GET /txinfos/:userAddress`

### Response
```javascript
{
    "balance": "1000",
    "nonce": 15,
    "gasPrice": "10000"
}
```

## Relay transaction
Sends a signed transaction

Remove txId as response instead compute on client

`POST /relay`

### Request
```javascript
// rawTransaction
```

### Response
```javascript
{
    "txId"
}
```

## `NEW` Get balance of externally owned account
Returns the ETH balance of an externally owned account

`GET /balances/:eoaAddress`

### Response
```javascript
{
    "balance": "12.1009234"
}
```

# Exchange API

## Get balances
Returns balances of user

`GET networks/:networkAddress/users/:userAddress/exchanges/:currency`

### Parameters
- `currency` -

### Response
```javascript
{
    "EUR": {
        "available": "1000", // available trustlines money
        "onOrders": "123", // amount on orders
        "ethValue": "1.12" // exchange value
    },
    "ETH": {
        "available": "123.112",
        "onOrders": "1.1112",
        "eurValue": "300"
    }
}
```

## Get deposits
Returns deposit history within range `start` to `end`

`GET networks/:networkAddress/users/:userAddress/exchanges/:currency/deposits?start=:start&end=:end`

### Parameters
- `start` - UNIX timestamp for range start
- `end` - UNIX timestamp for range end

### Response
```javascript
[
    {
        "currency": "ETH",
        "address": "...",
        "amount": "1.2323",
        "confirmations": 10,
        "txId": "...",
        "timestamp": 1399305798,
        "status": "COMPLETE"
    },
    // other deposits
]
```

## Get withdrawals
Returns withdrawal history within range `start` to `end`

`GET networks/:networkAddress/users/:userAddress/exchanges/:currency/withdrawals?start=:start&end=:end`

### Parameters
- `start` - UNIX timestamp for range start
- `end` - UNIX timestamp for range end

### Response
```javascript
[
    {
        "currency": "ETH",
        "address": "...",
        "amount": "1.2323",
        "confirmations": 10,
        "txId": "...",
        "timestamp": 1399305798,
        "status": "COMPLETE"
    },
    // other deposits
]
```

## Get open orders
Returns open orders for pair NetworkCurrency_ExchangeCurrency (i.e. EUR_ETH)

`GET networks/:networkAddress/users/:userAddress/exchanges/:currency/openorders`

### Response
```javascript
[
    {
        "orderNumber": 123456,
        "type": "SELL", // BUY or SELL
        "rate": "0.025", // exchange rate
        "amount": "100", // amount or order
        "total": "2.5", // total order price
        "timestamp": 1399305798
    },
    // other open orders
]
```

## Get trade history
Returns trade history within range `start` and `end`

`GET networks/:networkAddress/users/:userAddress/exchanges/:currency/orders?start=:startTimestamp&end=:endTimestamp`

### Parameters
- `start` - UNIX timestamp for range start
- `end` - UNIX timestamp for range end

### Response
```javascript
[
    {
        "orderNumber": 123456,
        "type": "SELL", // BUY or SELL
        "rate": "0.025", // exchange rate
        "amount": "100", // amount or order
        "total": "2.5", // total order price
        "fee": "0.00002", // fee of order
        "timestamp": 1399305798
    },
    // other deposits
]
```

## Place buy order
Places a limit buy order

`POST networks/:networkAddress/users/:userAddress/exchanges/:currency/`
