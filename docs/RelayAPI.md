# trustlines network REST API
The relay component of the trustlines network project provides a REST API.

## Base Endpoint
```
<protocol>://<host>:<port>/api/v1
```
You can use the following base endpoint to talk to the currently deployed KOVAN test setup.
```
https://relay0.testnet.trustlines.network/api/v1
```

## Response
- All endpoints return JSON
- All number values are returned in their smallest unit
- All ethereum addresses are returned as ERC55 checksum addresses
- In case of an error, the response of the relay API will have the following format:
```json
{
  "message": "<errorMessage>"
}
```

## API Endpoints
### Network context
- [Currency networks list](#currency-networks-list)
- [Currency network details](#currency-network-details)
- [Users list in currency network](#users-list-in-currency-network)
- [User details in currency network](#user-details-in-currency-network)
- [Trustlines of user in currency network](#trustlines-of-user-in-currency-network)
- [Trustline details of user in currency network](#trustline-details-of-user-in-currency-network)
- [Spendable amount and path to any user in currency network](#spendable-amount-and-path-to-any-user-in-currency-network)
- [Transfer path in currency network](#transfer-path-in-currency-network)
- [Closing trustline path in currency network](#closing-trustline-path-in-currency-network)
- [All events in currency network](#all-events-in-currency-network)
- [Events of a user in currency network](#events-of-a-user-in-currency-network)
### User context
- [Events of user in all currency networks](#events-of-user-in-all-currency-networks)
- [Transaction infos for user](#transaction-infos-for-user)
- [Balance of user](#balance-of-user)
### Other
- [Latest block number](#latest-block-number)
- [Relay transaction](#relay-transaction)
- [Relay meta transaction](#relay-meta-transaction)
- [Deploy identity contract](#deploy-identity-contract)
- [Get authorized identity factories](#get-authorized-identity-factories)
- [Get identity information](#get-identity-information)
- [Get relay version](#get-relay-version)

---

### Currency networks list
Returns all registered currency networks with high-level information.
#### Request
```
GET /networks
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks
```
#### Response
|Attribute      |Type   |JSON Type  |Description|
|-----------    |----   |---------  |----------|
|name           |string |string     |Full name of the currency network|
|abbreviation   |string |string     |Abbreviated name of currency network|
|address        |address|string - hex-encoded prefixed with "0x"   |Contract address of currency network|
#### Example Response
```json
[
  {
    "name": "Hours",
    "abbreviation": "HOU",
    "address": "0xC0B33D88C704455075a0724AA167a286da778DDE"
  },
  {
    "name": "Fugger",
    "abbreviation": "FUG",
    "address": "0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9"
  }
]
```

---

### Currency network details
Returns detailed information of currency network.
#### Request
```
GET /networks/:networkAddress
```
#### URL Parameters
|Name           |Type                     |Required   |Description|
|----           |----                     |--------   |-----------|
|networkAddress |string prefixed with "0x"|YES        |Address of currency network|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE
```
#### Response
|Attribute                  |Type  |JSON Type                               |Description|
|---------                  |----  |-----------                             |---------|
|abbreviation               |string|string                                  |Abbreviated name of currency network|
|address                    |address|string - hex-encoded prefixed with "0x"|Contract address of currency network|
|decimals                   |int   |number                                  |Decimals specified in currency network|
|name                       |string|string                                  |Full name of the currency network|
|numUsers                   |int   |number                                  |Total number of users in currency network|
|defaultInterestRate        |BigInteger|string                              |The default interest rate for every user in the network|
|interestRateDecimals       |int   |number                                  |Decimals of the interest rate|
|customInterests            |bool  |bool|Whether custom interest rate can be set by users|
|preventMediatorInterests   |bool  |bool|Whether to prevent mediators from paying interest|
#### Example Response
```json
{
  "abbreviation": "HOU",
  "address": "0xC0B33D88C704455075a0724AA167a286da778DDE",
  "decimals": 2,
  "name": "Hours",
  "numUsers": 3,
  "defaultInterestRate": "100",
  "interestRateDecimals": 2,
  "customInterests": false,
  "preventMediatorInterests": false
}
```

---

### Users list in currency network
Returns a list of user addresses in a currency network.
#### Request
```
GET /networks/:networkAddress/users
```
#### URL Parameters
|Name|Type|Required|Description|
|----|----|--------|-----------|
|networkAddress|string|YES|Address of currency network|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users
```
#### Response
`string[]` - Array with addresses of users in currency network
#### Example Response
```json
[
  "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
  "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
  "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b"
]
```

---

### User details in currency network
Returns detailed information of a user in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddress
```
#### URL Parameters
|Name|Type|Required|Description|
|----|----|--------|-----------|
|networkAddress|string|YES|Address of currency network|
|userAddress|string|YES|Address of user|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce
```
#### Response
| Attribute     | Type       | JSON Type | Description                                                                  |
| ---------     | ---------- | ------    | ---------------------------------------------                                |
| balance       | BigInteger | string    | Sum over balances of all non-frozen trustlines user has in currency network  |
| frozenBalance | BigInteger | string    | Sum over balances of all frozen trustlines user has in currency network      |
| given         | BigInteger | string    | Sum of all creditlines given by user in currency network                     |
| received      | BigInteger | string    | Sum of all creditlines received by user in currency network                  |
| leftGiven     | BigInteger | string    | given - balance                                                              |
| leftReceived  | BigInteger | string    | received + balance                                                           |
#### Example Response
```json
{
  "balance": "-1000",
  "frozenBalance": "1000",
  "given": "2000",
  "received": "4000",
  "leftGiven": "3000",
  "leftReceived": "1000"
}
```

---

### Trustlines of user in currency network
Returns a list of trustlines a user has in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddress/trustlines
```
#### URL Parameters
|Name|Type|Required|Description|
|----|----|--------|-----------|
|networkAddress|string|YES|Address of currency network|
|userAddress|string|YES|Address of user|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/trustlines
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|counterParty|string|Address of trustline counterparty|
|user|string|Address of trustline user|
|balance|string|Balance of trustline from point of view of user|
|given|string|Creditline given to counterparty|
|received|string|Creditline received by counterparty|
|leftGiven|string|given - balance|
|leftReceived|string|received + balance|
|interestRateGiven|string|Interest Rate given to counterparty|
|interestRateReceived|string|Interest Rate received from counterparty|
|isFrozen|bool|Whether the trustlines is frozen|
|id|string|Identifier of trustline|
#### Example Response
```json
[
  {
    "id": "0xe4332c0bc15bf97933ce54c93af772bb13fad2c4c44e2516eb62d4f6c041e9ab",
    "leftReceived": "19848",
    "counterParty": "0xB5A3ad8d5A23e5DDD8b8917F709b01396e4d55e4",
    "balance": "-152",
    "given": "10000",
    "leftGiven": "10152",
    "received": "20000",
    "interestRateGiven": "1000",
    "interestRateReceived": "2000",
    "isFrozen": false,
    "user": "0x04f9b217b334507c42Ad3b74BFf024c724aBB166"
  }
]
```

---

### Trustline of user in currency network
Returns a trustline between users A and B in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddressA/trustlines/:userAddressB
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
|userAddressA|string|YES|Address of user A|
|userAddressB|string|YES|Address of user B|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/trustlines/0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b
```
### Response
|Attribute|Type|Description|
|---------|----|-----------|
|counterParty|string|Address of trustline counterparty|
|user|string|Address of trustline user|
|balance|string|Balance of trustline from point of view of user (A)|
|given|string|Creditline given to counterparty|
|received|string|Creditline received by counterparty|
|leftGiven|string|given - balance|
|leftReceived|string|received + balance|
|interestRateGiven|string|Interest Rate given to counterparty|
|interestRateReceived|string|Interest Rate received from counterparty|
|isFrozen|bool|Whether the trustline is forzen|
|id|string|Identifier of trustline|
### Example Response
```json
{
    "id": "0xe4332c0bc15bf97933ce54c93af772bb13fad2c4c44e2516eb62d4f6c041e9ab",
    "leftReceived": "19848",
    "counterParty": "0xB5A3ad8d5A23e5DDD8b8917F709b01396e4d55e4",
    "balance": "-152",
    "given": "10000",
    "leftGiven": "10152",
    "received": "20000",
    "interestRateGiven": "1000",
    "interestRateReceived": "2000",
    "isFrozen": false,
    "user": "0x04f9b217b334507c42Ad3b74BFf024c724aBB166"
}
```

---

### Spendable amount and path to any user in currency network
Returns an estimation on the amount user A can spend to any reachable user B in a currency network.
#### Request
```
POST /networks/:network_address/max-capacity-path-info
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
#### Data Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|from|string|YES|Address of user who sends transfer|
|to|string|YES|Address of user who receives transfer|
|maxHops|string|NO|Upper bound for hops in transfer path|
#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"from":"0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce","to":"0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b"}' \
  https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/max-capacity-path-info
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|capacity|string|Estimated capacity of estimated max capacity path|
|path|string[]|Addresses of users on max capacity path|
#### Example Response
```json
{
    "capacity": "18",
	"path": [
    "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
    "0xc257274276a4e539741ca11b590b9447b26a8051",
    "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b"
  ]
}
```

---

### Transfer path in currency network
Returns the cheapest path and maximal fees for a transfer.
#### Request
```
POST /networks/:networkAddress/path-info
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
#### Data Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|from|string|YES|Address of user who sends transfer|
|to|string|YES|Address of user who receives transfer|
|value|string|YES|Transfer amount in smallest unit|
|maxFees|string|NO|Upper bound for transfer fees|
|maxHops|string|NO|Upper bound for hops in transfer path|
|feePayer|string|NO|Either `sender` or `receiver`|
#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"from":"0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce","to":"0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b", "value": "1000"}' \
  https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/path-info
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|path|string[]|Addresses of users on transfer path|
|value|int|Transfer amount in smallest unit|
|feePayer|string|Either `sender` or `receiver`|
|fees|string|Maximal transfer fees|
#### Example Response
```json
{
	"path": [
    "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
    "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b"
  ],
  "value": 1000,
  "fees": "2",
  "feePayer": "sender"
}
```

---

### Closing trustline path in currency network
This endpoint is used in preparation for closing a trustline. It returns the
cheapest path, the fees and a value for a payment,
which reduces the balance to zero. At the moment this only works for negative
balances.

#### Request
```
POST /networks/:networkAddress/close-trustline-path-info
```
#### URL Parameters
| Name           | Type   | Required | Description                 |
|----------------|--------|----------|-----------------------------|
| networkAddress | string | YES      | Address of currency network |
#### Data Parameters
| Name    | Type   | Required | Description                                              |
|---------|--------|----------|----------------------------------------------------------|
| from    | string | YES      | Address of user who wants to close a trustline           |
| to      | string | YES      | Address of user with whom the trustline should be closed |
| maxFees | string | NO       | Upper bound for transfer fees                            |
| maxHops | string | NO       | Upper bound for hops in transfer path                    |

#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"from":"0x186ec4A5E2c9Ed2B392599843375383D40C94F57","to":"0xaE8446e5ea18F6d7647b28eEf01e568BE672AF6c"}' \
https://relay0.testnet.trustlines.network/api/v1/networks/0xc5F45B680e81759E3FBc4b4a5A94FBd40BAB3fAd/close-trustline-path-info
```
#### Response
| Attribute    | Type     | Description                               |
|--------------|----------|-------------------------------------------|
| path         | string[] | Addresses of users on transfer path       |
| fees         | string   | Estimated transfer fees                   |
| value        | string   | Amount to be transferred in smallest unit |
| feePayer     | string   | Either `sender` or `receiver` |

#### Example Response
```json
{
    "fees": "6",
    "path": [
        "0x186ec4A5E2c9Ed2B392599843375383D40C94F57",
        "0x37605B30874452551F959811C5F8662329E51EB2",
        "0xaE8446e5ea18F6d7647b28eEf01e568BE672AF6c",
        "0x186ec4A5E2c9Ed2B392599843375383D40C94F57"
    ],
    "value": "410",
    "feePayer": "sender"
}
```

---

### All events in currency network
Returns a list of event logs in a currency network.
#### Request
```
GET /networks/:networkAddress/events?type=:type&fromBlock=:fromBlock
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/events?type=TrustlineUpdate&fromBlock=123456
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|networkAddress|string|Address of currency network|
|blockNumber|string|Number of block|
|timestamp|int|UNIX timestamp|
|type|string|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|from|string|Address of `from` user|
|to|string|Address of `to` user|
|status|string| `sent`, `pending` or `confirmed` depending on block height|
|transactionId|string|Transaction hash|

Following additional attributes for `TrustlineUpdate` and `TrustlineUpdateRequest` events:

| Attribute            | Type   | Description                                        |
|----------------------|--------|----------------------------------------------------|
| given                | string | Proposed or accepted amount `from -> to`           |
| received             | string | Proposed or accepted amount `to -> from`           |
| interestRateGiven    | string | Proposed or accepted rate of interests `from -> to`|
| interestRateReceived | string | Proposed or accepted rate of interests `to -> from`|
| isFrozen             | bool   | Proposed or accepted frozen status                 |

Following additional attributes for `Transfer` events:

| Attribute | Type   | Description                                          |
|-----------|--------|------------------------------------------------------|
| amount    | string | Transfer amount `from -> to`                         |
| extraData | string | extraData as specified in the corresponding transfer |
|           |        |                                                      |
#### Example Response
```json
[
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997877,
		"timestamp": 1524655432,
		"type": "TrustlineUpdateRequest",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
		"status": "confirmed",
		"transactionId": "0xb141aa3baec4e7151d8bd6ecab46d26b1add131e50bcc517c956a7ac979815cd",
		"given": "20000",
		"received": "20000",
		"interestRateGiven": "1000",
		"interestRateReceived": "1000",
        "isFrozen": false
	},
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997899,
		"timestamp": 1524655600,
		"type": "TrustlineUpdate",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x10d4e9acb58d42d433dbc5c995e9a258cd2bb7fe82fedf2ebab82e450d30c643",
		"given": "10000",
		"received": "10000",
		"interestRateGiven": "1000",
		"interestRateReceived": "1000",
        "isFrozen": false
	},
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 7011809,
		"timestamp": 1524755036,
		"type": "Transfer",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x05c91f6506e78b1ca2413df9985ca7d37d2da5fc076c0b55c5d9eb9fdd7513a6",
		"amount": "100",
		"extraData": "0x1234"
	}
]
```

---

### Events of a user in currency network
Returns a list of event logs of a user in a currency network. This means all events where the given user address is either `from` or `to`.
#### Request
```
GET /networks/:network/users/:user/events?type=:type&fromBlock=:fromBlock
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/events?type=TrustlineUpdate&fromBlock=123456
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|user|string|YES|Address of user|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|networkAddress|string|Address of currency network|
|blockNumber|string|Number of block|
|timestamp|int|UNIX timestamp|
|type|string|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|from|string|Address of `from` user|
|to|string|Address of `to` user|
|status|string| `sent`, `pending` or `confirmed` depending on block height|
|transactionId|string|Transaction hash|

Following additional attributes for `TrustlineUpdate` and `TrustlineUpdateRequest` events:

| Attribute            | Type   | Description                                        |
|----------------------|--------|----------------------------------------------------|
| given                | string | Proposed or accepted amount `from -> to`           |
| received             | string | Proposed or accepted amount `to -> from`           |
| interestRateGiven    | string | Proposed or accepted rate of interests `from -> to`|
| interestRateReceived | string | Proposed or accepted rate of interests `to -> from`|
| isFrozen             | bool   | Proposed or accepted frozen state                 |

Following additional attributes for `Transfer` events:

| Attribute | Type   | Description                                          |
|-----------|--------|------------------------------------------------------|
| amount    | string | Transfer amount `from -> to`                         |
| extraData | string | extraData as specified in the corresponding transfer |

#### Example Response
```json
[
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997877,
		"timestamp": 1524655432,
		"type": "TrustlineUpdateRequest",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
		"status": "confirmed",
		"transactionId": "0xb141aa3baec4e7151d8bd6ecab46d26b1add131e50bcc517c956a7ac979815cd",
		"given": "20000",
		"received": "20000",
		"interestRateGiven": "1000",
		"interestRateReceived": "1000",
        "isFrozen": false
	},
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997899,
		"timestamp": 1524655600,
		"type": "TrustlineUpdate",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x10d4e9acb58d42d433dbc5c995e9a258cd2bb7fe82fedf2ebab82e450d30c643",
		"given": "10000",
		"received": "10000",
		"interestRateGiven": "1000",
		"interestRateReceived": "1000",
        "isFrozen": false
	},
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 7011809,
		"timestamp": 1524755036,
		"type": "Transfer",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x05c91f6506e78b1ca2413df9985ca7d37d2da5fc076c0b55c5d9eb9fdd7513a6",
		"amount": "100",
		"extraData": "0x1234"
	}
]
```

---

### Events of user in all currency networks
Returns a list of event logs of an user in all currency networks. That means all events where the given user address is either `from` or `to`.
#### Request
```
GET /users/:user/events?type=:type&fromBlock=:fromBlock
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/events?type=TrustlineUpdate&fromBlock=123456
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|user|string|YES|Address of user|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|networkAddress|string|Address of currency network|
|blockNumber|string|Number of block|
|timestamp|int|UNIX timestamp|
|type|string|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|from|string|Address of `from` user|
|to|string|Address of `to` user|
|status|string| `sent`, `pending` or `confirmed` depending on block height|
|transactionId|string|Transaction hash|

Following additional attributes for `TrustlineUpdate` and `TrustlineUpdateRequest` events:

| Attribute            | Type   | Description                                        |
|----------------------|--------|----------------------------------------------------|
| given                | string | Proposed or accepted amount `from -> to`           |
| received             | string | Proposed or accepted amount `to -> from`           |
| interestRateGiven    | string | Proposed or accepted rate of interests `from -> to`|
| interestRateReceived | string | Proposed or accepted rate of interests `to -> from`|
| isFrozen             | bool   | Proposed or accepted frozen status                 |

Following additional attributes for `Transfer` events:

| Attribute | Type   | Description                                          |
|-----------|--------|------------------------------------------------------|
| amount    | string | Transfer amount `from -> to`                         |
| extraData | string | extraData as specified in the corresponding transfer |

#### Example Response
```json
[
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997877,
		"timestamp": 1524655432,
		"type": "TrustlineUpdateRequest",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
		"status": "confirmed",
		"transactionId": "0xb141aa3baec4e7151d8bd6ecab46d26b1add131e50bcc517c956a7ac979815cd",
		"given": "20000",
		"received": "20000",
		"interestRateGiven": "1000",
		"interestRateReceived": "1000",
        "isFrozen": false
	},
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997899,
		"timestamp": 1524655600,
		"type": "TrustlineUpdate",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x10d4e9acb58d42d433dbc5c995e9a258cd2bb7fe82fedf2ebab82e450d30c643",
		"given": "10000",
		"received": "10000",
		"interestRateGiven": "1000",
		"interestRateReceived": "1000",
        "isFrozen": false
	},
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 7011809,
		"timestamp": 1524755036,
		"type": "Transfer",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x05c91f6506e78b1ca2413df9985ca7d37d2da5fc076c0b55c5d9eb9fdd7513a6",
		"amount": "100",
		"extraData": "0x1234"
	}
]
```

---

### Balance of user
Returns the balance in ether of the given address.
#### Request
```
GET /users/:userAddress/balance
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/balance
```
#### URL Parameters
| Name        | Type   | Required | Description     |
| ----------- | ------ | -------- | --------------- |
| userAddress | string | YES      | Address of user |
#### Response
| Attribute | Type   | JSON Type | Description            |
| --------- | ------ | --------- | ---------------------- |
| balance   | string | string    | Balance of user in eth |
#### Example Response
```json
{
  "balance": "2.377634165348042492"
}
```

---

### Transaction infos for user
Returns information that is needed to sign a transaction.
#### Request
```
GET /users/:userAddress/txinfos
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/txinfos
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|userAddress|string|YES|Address of user|
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|gasPrice|string|Gas price|
|balance|string|Balance of user in wei|
|nonce|int|Nonce needed for creating a transaction|
#### Example Response
```json
{
  "gasPrice": 0,
  "balance": "2377634165348042492",
  "nonce": 58
}
```

---

### Latest block number
Returns the latest block number.
#### Request
```
GET /blocknumber
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/blocknumber
```
#### Response
`int` - Latest block number
#### Example Response
```json
7426584
```

---

### Relay transaction
Relays a raw transaction to the blockchain.
#### Request
```
POST /relay
```
#### Data Parameters
|Name|Type|Required|Description|
|----|----|--------|-----------|
|rawTransaction|string|YES|RLP encoded signed transaction|
#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"rawTransaction":"<rawTxString>"}' \
  https://relay0.testnet.trustlines.network/api/v1/relay
```
#### Response
`string` - hash of transaction if relayed successfully
#### Example Response
```json
"<tx hash>"
```

---

### Relay meta transaction
Relays a meta transaction to the blockchain.
#### Request
```
POST /relay-meta-transaction
```
#### Data Parameters
| Name            | Type                   | Required | Description            |
|-----------------|------------------------|----------|------------------------|
| metaTransaction | object                 | YES      | MetaTransaction object |


The MetaTransaction object must have the following fields:

| Name       | Type     | JSON Type                                 | Description |
|------------|--------- |-------------------------------------------|-------------|
| from       | address  | string - hex-encoded prefixed with "0x"   | address of identity contract |
| to         | address  | string - hex-encoded prefixed with "0x"   | the address on which the call of the meta transaction is happening |
| value      |BigInteger| string                                    | the amount of wei to be sent along from 'from' to 'to'             |
| data       | bytes    | string - hex-encoded prefixed with "0x"   | the data object encoding the function call including arguments     |
| nonce      | int      | number                                    | nonce used for replay protection                                   |
| extraData  | bytes    | string - hex-encoded prefixed with "0x"   | bytes extra data for backwards compatibility                       |
| signature  | bytes    | string - hex-encoded prefixed with "0x"   | 65 bytes containing concatenated. v,r,s of the signature           |

#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"metaTransaction": {"value": "0", "to": "0x51a240271AB8AB9f9a21C82d9a85396b704E164d", "nonce": "1", "data": "0x46432830000000000000000000000000000000000000000000000000000000000000000a", "from": "0xF2E246BB76DF876Cef8b38ae84130F4F55De395b", "signature": "0x6d2fe56ef6648cb3f0398966ad3b05d891cde786d8074bdac15bcb92ebfa7222489b8eb6ed87165feeede19b031bb69e12036a5fa13b3a46ad0c2c19d051ea9101", "extraData": "0x"}}' \
  https://relay0.testnet.trustlines.network/api/v1/relay-meta-transaction
```
#### Response
```json
"<tx hash>"
```
---

### Deploy identity contract
This endpoint can be used to deploy an identity contract to the blockchain.

#### Request
```
POST /identities
```
#### Data Parameters
| Name         | Type    | JSON Type                                 | Required | Description            |
|--------------|---------|-------------------------------------------|----------| ---------- |
| ownerAddress | address | string - hex-encoded prefixed with "0x"   |YES       | MetaTransaction object |



#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"ownerAddress": "0xF2E246BB76DF876Cef8b38ae84130F4F55De395b"}' \
  https://relay0.testnet.trustlines.network/api/v1/identities
```
#### Response
The endpoint returns an object with the following fields:

| Name      | Type       | JSON Type                                 | Description                                   |
|-----------|------------|-------------------------------------------|-----------------------------------------------|
| identity  | address    | string - hex-encoded prefixed with "0x"   | the address of the deployed identity contract |
| nextNonce | number     | number                                    | the next available nonce                      |
| balance   | BigInteger | string                                    | contracts balance in wei                      |

#### Example Response
```json
{"identity": "0x43950642C8685ED8e3Fb89a5C5aeCb12862A87fd", "nextNonce": 0, "balance": "0"}
```

### Get authorized identity factories
#### Request
```
GET /factories
```

#### Example Request
```bash
curl https://relay0.testnet.trustlines.network/api/v1/factories
```

#### Response
`string[]`: list of known identity factories through which identity deployment is possible

#### Example Response
```
["0x43950642C8685ED8e3Fb89a5C5aeCb12862A87fd"]
```

### Get identity information
#### Request
```
GET /identities/:identity
```
#### URL Parameters

| Name     | Type                      | Required | Description                                   |
|----------|---------------------------|----------|-----------------------------------------------|
| identity | string prefixed with "0x" | YES      | the address of the deployed identity contract |

#### Example Request
```bash
curl https://relay0.testnet.trustlines.network/api/v1/identities/0x2AbCc1389258Dc187DB787E33FD2B99d53695DE3
```

#### Response
The endpoint returns an object with the following fields:

| Name      | Type       | JSON Type                                 | Description                                   |
|-----------|---------   |-------------------------------------------|-----------------------------------------------|
| identity  | string     | string - hex-encoded prefixed with "0x"   | the address of the deployed identity contract |
| nextNonce | int        | number                                    | the next available nonce                      |
| balance   | BigInteger | string                                    | contracts balance in wei                      |
#### Example Response
```json
{"identity": "0x2AbCc1389258Dc187DB787E33FD2B99d53695DE3", "nextNonce": 0, "balance": "0"}
```

### Get relay version
#### Request
```
GET /version
```

#### Example Request
```bash
curl https://relay0.testnet.trustlines.network/api/v1/version
```

#### Response
`string`: relay version

#### Example Response
```
relay/v0.7.0
```
