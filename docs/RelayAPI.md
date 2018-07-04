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
- [Total spendable amount of user in currency network](#total-spendable-amount-of-user-in-currency-network)
- [Spendable amount to other user in currency network](#spendable-amount-to-other-user-in-currency-network)
- [Transfer path in currency network](#transfer-path-in-currency-network)
- [Debt reduction path in currency network](#debt-reduction-path-in-currency-network)
- [All events in currency network](#all-events-in-currency-network)
- [Events of user in currency network](#events-of-user-in-currency-network)
### User context
- [Events of user in all currency networks](#events-of-user-in-all-currency-networks)
- [Transaction infos for user](#transaction-infos-for-user)
### Other
- [Latest block number](#latest-block-number)
- [Relay transaction](#relay-transaction)

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
|Attribute|Type|Description|
|---------|----|-----------|
|name|string|Full name of the currency network|
|abbreviation|string|Abbreviated name of currency network|
|address|string|Contract address of currency network|
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
|Name|Type|Required|Description|
|----|----|--------|-----------|
|networkAddress|string|YES|Address of currency network|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|abbreviation|string|Abbreviated name of currency network|
|address|string|Contract address of currency network|
|decimals|int|Decimals specified in currency network|
|name|string|Full name of the currency network|
|numUsers|int|Total number of users in currency network|
#### Example Response
```json
{
  "abbreviation": "HOU",
  "address": "0xC0B33D88C704455075a0724AA167a286da778DDE",
  "decimals": 2,
  "name": "Hours",
  "numUsers": 3
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
|-|-|-|-|
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
Returns detailed information of an user in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddress
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
|userAddress|string|YES|Address of user|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|balance|string|Sum over balances of all trustlines user has in currency network|
|given|string|Sum of all creditlines given by user in currency network|
|received|string|Sum of all creditlines received by user in currency network|
|leftGiven|string|given - balance|
|leftReceived|string|received + balance|
#### Example Response
```json
{
	"balance": "-1000",
  "given": "2000",
  "received": "3000",
  "leftGiven": "3000",
  "leftReceived": "1000"
}
```

---

### Trustlines of user in currency network
Returns a list of trustlines an user has in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddress/trustlines
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
|userAddress|string|YES|Address of user|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/trustlines
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|address|string|Address of trustline counterparty|
|balance|string|Balance of trustline from point of view of user|
|given|string|Creditline given to counterparty|
|received|string|Creditline received by counterparty|
|leftGiven|string|given - balance|
|leftReceived|string|received + balance|
|id|string|Identifier of trustline|
#### Example Response
```json
[
	{
		"address": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"balance": "-102",
		"given": "10000",
		"received": "10000",
		"leftGiven": "10102",
		"leftReceived": "9898",
		"id": "0x314338891c370d4c77657386c676b6cd2e4862af1244820f9e7b9166d181057f"
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
|address|string|Address of trustline counterparty (B)|
|balance|string|Balance of trustline from point of view of user (A)|
|given|string|Creditline given to counterparty|
|received|string|Creditline received by counterparty|
|leftGiven|string|given - balance|
|leftReceived|string|received + balance|
|id|string|Identifier of trustline|
### Example Response
```json
{
	"address": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
	"balance": "-102",
	"given": "10000",
	"received": "10000",
	"leftGiven": "10102",
	"leftReceived": "9898",
	"id": "0x314338891c370d4c77657386c676b6cd2e4862af1244820f9e7b9166d181057f"
}
```

---

### Total spendable amount of user in currency network
Returns the total amount a user can spend in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddress/spendable
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
|userAddress|string|YES|Address of user|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/spendable
```
#### Response
`string` - Total amount in smallest unit user can spend in a currency network
#### Example Response
```json
"1000"
```

---

### Spendable amount to other user in currency network
Returns amount user A can spend to user B in a currency network.
#### Request
```
GET /networks/:networkAddress/users/:userAddressA/spendables/:userAddressB
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
|userAddressA|string|YES|Address of user A|
|userAddressB|string|YES|Address of user B|
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/spendables/0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b
```
#### Response
`string` - Amount user A can spend to user B in a currency network
#### Example Response
```json
"90"
```

---

### Transfer path in currency network
Returns the cheapest path, the estimated gas costs and maximal fees for a transfer.
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
|fees|string|Maximal transfer fees|
|estimatedGas|int|Estimated gas costs for transfer|
#### Example Response
```json
{
	"path": [
    "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
    "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b"
  ],
  "fees": "2",
  "estimatedGas": 76324
}
```

---

### Debt reduction path in currency network
Returns the cheapest path, the estimated gas costs and estimated fees for a debt reduction transfer.
#### Request
```
POST /networks/:networkAddress/reduce-debt-path-info
```
#### URL Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|networkAddress|string|YES|Address of currency network|
#### Data Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|from|string|YES|Address of user who wants to reduce debt|
|to|string|YES|Address of user who sees debt reduce|
|via|string|YES|Address of intermediary used to reduce debt|
|value|string|YES|Amount for debt reduction in smallest unit|
|maxFees|string|NO|Upper bound for transfer fees|
|maxHops|string|NO|Upper bound for hops in transfer path|
#### Example Request
```bash
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"from":"0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce","to":"0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b","via":0xc257274276a4e539741ca11b590b9447b26a8051, "value": "1000"}' \
  https://relay0.testnet.trustlines.network/api/v1/networks/0xC0B33D88C704455075a0724AA167a286da778DDE/reduce-debt-path-info
```
#### Response
|Attribute|Type|Description|
|---------|----|-----------|
|path|string[]|Addresses of users on transfer path|
|fees|string|Estimated transfer fees|
|estimatedGas|int|Estimated gas costs for transfer|
#### Example Response
```json
{
	"path": [
    "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
    "0xc257274276a4e539741ca11b590b9447b26a8051",
    "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
    "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce"
  ],
  "fees": "2",
  "estimatedGas": 76324
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
|Attribute|Type|Description|
|---------|----|-----------|
|given|string|Proposed or accepted amount `from -> to`|
|received|string|Proposed or accepted amount `to -> from`|

Following additional attributes for `Transfer` events:
|Attribute|Type|Description|
|---------|----|-----------|
|amount|string|Transfer amount `from -> to`|
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
		"received": "20000"
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
		"received": "10000"
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
		"amount": "100"
	}
]
```

---

### Events of a user in currency network
Returns a list of event logs of an user in a currency network. That means all events where the given user address is either `from` or `to`.
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
|Attribute|Type|Description|
|---------|----|-----------|
|given|string|Proposed or accepted amount `from -> to`|
|received|string|Proposed or accepted amount `to -> from`|

Following additional attributes for `Transfer` events:
|Attribute|Type|Description|
|---------|----|-----------|
|amount|string|Transfer amount `from -> to`|
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
		"received": "20000"
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
		"received": "10000"
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
		"amount": "100"
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
|Attribute|Type|Description|
|---------|----|-----------|
|given|string|Proposed or accepted amount `from -> to`|
|received|string|Proposed or accepted amount `to -> from`|

Following additional attributes for `Transfer` events:
|Attribute|Type|Description|
|---------|----|-----------|
|amount|string|Transfer amount `from -> to`|
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
		"received": "20000"
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
		"received": "10000"
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
		"amount": "100"
	}
]
```

---

### Transaction infos of user
Returns information that is needed to sign a transaction.
#### Request
```
GET /users/:userAddress/tx-infos
```
#### Example Request
```
curl https://relay0.testnet.trustlines.network/api/v1/users/0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce/tx-infos
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

### Relay
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
