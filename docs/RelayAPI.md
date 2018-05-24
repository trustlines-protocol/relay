# trustlines network REST API
The relay component of the trustlines network project provides a REST API.

## Base Endpoint
```
<protocol>://<host>:<port>/api/v1
```
You can use the following base endpoint to talk to the currently deployed KOVAN test setup.
```
https://relay0.testnet.trustlines.network:443/api/v1
```

## Response
- All endpoints return either a number, a JSON object or an array
- All number values are returned in their smallest unit
- In case of an error, the response of the relay API will have the following format:
```javascript
{
  "message": "<errorMessage>"
}
```

## API Endpoints
### Network context
- [Currency networks list](##/networks)
- [Currency network details](##/networks/:network)
- [Users list in currency network](##/networks/:network/users)
- [User details in currency network](##/networks/:network/users/:user)
- [Trustlines of user in currency network](##/networks/:network/users/:user/trustlines)
- [Trustline details of user in currency network](##/networks/:network/users/:userA/trustlines/:userB)
- [Total spendable amount of user in currency network](##/networks/:network/users/:userA/spendable)
- [Spendable amount to other user in currency network](##/networks/:network/users/:userA/spendables/:userB)
- [Transfer path in currency network](##/networks/:network/path-info)
- [All events in currency network](##/networks/:network/events)
- [Events of user in currency network](##/networks/:network/users/:user/events)
### User context
- [Events of user in all currency networks](##/users/:user/events)
- [Transaction infos for user](##/users/:user/txinfos)
### Other
- [Latest block number](###/blocknumber)
- [Relay](###/relay)
---

### Currency networks list
### `/networks`
Returns all registered currency networks with high-level information.
#### Request
```
GET /networks
```
#### Response
```javascript
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
### `/networks/:network`
Returns detailed information of currency network.
#### Request
```
GET /networks/:network
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
#### Response
```javascript
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
### `/networks/:network/users`
Returns a list of user addresses in a currency network.
#### Request
```
GET /networks/:network/users
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
#### Response
```javascript
[
  "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
  "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
  "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
	...
]
```

---

### User details in currency network 
### `/networks/:network/users/:user`
Returns detailed information of an user in a currency network.
#### Request
```
GET /networks/:network/users/:user
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|user|string|YES|Address of user|
#### Response
```javascript
{
	"balance": -1000, // sum over balances of all trustlines user has in currency network
  "given": 2000, // sum of all creditlines given by user in currency network
  "received": 3000, // sum of all creditlines received by user in currency network
  "leftGiven": 3000, // given - balance
  "leftReceived": 1000 // received + balance
}
```

---

### Trustlines of user in currency network
### `/networks/:network/users/:user/trustlines`
Returns a list of trustlines an user has in a currency network.
#### Request
```
GET /networks/:network/users/:user/trustlines
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|user|string|YES|Address of user|
### Response
```javascript
[
	{
		"address": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b", // address of trustline counterparty
		"balance": -102, // balance of trustline from POV of user
		"given": 10000,  // credit line given to counterparty
		"received": 10000, // credit line received by counterparty
		"leftGiven": 10102, // given - balance
		"leftReceived": 9898, // received - balance
		"id": "0x314338891c370d4c77657386c676b6cd2e4862af1244820f9e7b9166d181057f" // identifier of trustline
	},
	... // other trustline objects
]
```

---

### Trustline of user in currency network
### `/networks/:network/users/:userA/trustlines/:userB`
Returns a trustline between users A and B in a currency network.
#### Request
```
GET /networks/:network/users/:userA/trustlines/:userB
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|userA|string|YES|Address of user A|
|userB|string|YES|Address of user B|
### Response
```javascript
{
	"address": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b", // address of trustline counterparty / user B
	"balance": -102, // balance of trustline from POV of user A
	"given": 10000,  // credit line given to counterparty
	"received": 10000, // credit line received by counterparty
	"leftGiven": 10102, // given - balance
	"leftReceived": 9898, // received - balance
	"id": "0x314338891c370d4c77657386c676b6cd2e4862af1244820f9e7b9166d181057f" // identifier of trustline
}
```

---

### Total spendable amount of user in currency network
### `/networks/:network/users/:user/spendable`
Returns the total amount a user can spend in a currency network.
#### Request
```
GET /networks/:network/users/:user/spendable
```
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|user|string|YES|Address of user|
### Response
```javascript
1000 // total amount user can spend in a currency network
```

---

### Spendable amount to other user in currency network
### `/networks/:network/users/:userA/spendables/:userB`
Returns amount user A can spend to user B in a currency network.
#### Request
```
GET /networks/:network/users/:userA/spendables/:userB
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|userA|string|YES|Address of user A|
|userB|string|YES|Address of user B|
### Response
```javascript
90 // amount user A can spend to user B in a currency network
```

---

### Transfer path in currency network
### `/networks/:network/path-info`
Returns the cheapest path, the estimated gas costs and maximal fees for a transfer.
#### Request
```
POST /networks/:network/path-info
```
### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
### POST body
|Name|Type|Required|Description|
|-|-|-|-|
|from|string|YES|Address of user who sends transfer|
|to|string|YES|Address of user who receives transfer|
|value|int|YES|Transfer amount in smallest unit|
|maxFees|int|NO|Upper bound for transfer fees|
|maxHops|int|NO|Upper bound for hops in transfer path|
### Response
```javascript
{
	"path": [
    "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce", // from address
		..., // hop addresses in path
    "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b" // to address
  ],
  "fees": 2, // maximal transfer fees
  "estimatedGas": 76324 // estimated gas costs for transfer
}
```

---

### All events in currency network
### `/networks/:network/events`
Returns a list of event logs in a currency network.
#### Request
```
GET /networks/:network/events?type=:type&fromBlock=:fromBlock
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Response
```javascript
[
	// TrustlineUpdateRequest
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997877,
		"timestamp": 1524655432, // UNIX timestamp
		"type": "TrustlineUpdateRequest",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
		"status": "confirmed", // sent || pending || confirmed depending on block height
		"transactionId": "0xb141aa3baec4e7151d8bd6ecab46d26b1add131e50bcc517c956a7ac979815cd", // transaction hash
		"given": "20000", // proposed amount [from -> to]
		"received": "20000" // proposed amount [from <- to]
	},
	// TrustlineUpdate
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997899,
		"timestamp": 1524655600,
		"type": "TrustlineUpdate",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x10d4e9acb58d42d433dbc5c995e9a258cd2bb7fe82fedf2ebab82e450d30c643",
		"given": "10000", // accepted amount [from -> to]
		"received": "10000" // accepted amount [from <- to]
	},
	// Transfer	
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 7011809,
		"timestamp": 1524755036,
		"type": "Transfer",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x05c91f6506e78b1ca2413df9985ca7d37d2da5fc076c0b55c5d9eb9fdd7513a6",
		"amount": "100" // transferred amount
	},
	... // more event objects
]
```

---

### Events of a user in currency network
### `/networks/:network/users/:user/events`
Returns a list of event logs of an user in a currency network. That means all events where the given user address is either `from` or `to`.
#### Request
```
GET /networks/:network/users/:user/events?type=:type&fromBlock=:fromBlock
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|network|string|YES|Address of currency network|
|user|string|YES|Address of user|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Response
```javascript
[
	// TrustlineUpdateRequest
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997877,
		"timestamp": 1524655432, // UNIX timestamp
		"type": "TrustlineUpdateRequest",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
		"status": "confirmed", // sent || pending || confirmed depending on block height
		"transactionId": "0xb141aa3baec4e7151d8bd6ecab46d26b1add131e50bcc517c956a7ac979815cd", // transaction hash
		"given": "20000", // proposed amount [from -> to]
		"received": "20000" // proposed amount [from <- to]
	},
	// TrustlineUpdate
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 6997899,
		"timestamp": 1524655600,
		"type": "TrustlineUpdate",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x10d4e9acb58d42d433dbc5c995e9a258cd2bb7fe82fedf2ebab82e450d30c643",
		"given": "10000", // accepted amount [from -> to]
		"received": "10000" // accepted amount [from <- to]
	},
	// Transfer	
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 7011809,
		"timestamp": 1524755036,
		"type": "Transfer",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x05c91f6506e78b1ca2413df9985ca7d37d2da5fc076c0b55c5d9eb9fdd7513a6",
		"amount": "100" // transferred amount
	},
	... // more event objects
]
```

---

### Events of user in all currency networks
### `/users/:user/events`
Returns a list of event logs of an user in all currency networks. That means all events where the given user address is either `from` or `to`.
#### Request
```
GET /users/:user/events?type=:type&fromBlock=:fromBlock
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|user|string|YES|Address of user|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Response
```javascript
[
	// TrustlineUpdateRequest
	{
		"networkAddress": "0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9",
		"blockNumber": 6997877,
		"timestamp": 1524655432, // UNIX timestamp
		"type": "TrustlineUpdateRequest",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ff66eb1A824FF9D1bB7e234a2d3B7A3b0345320",
		"status": "confirmed", // sent || pending || confirmed depending on block height
		"transactionId": "0xb141aa3baec4e7151d8bd6ecab46d26b1add131e50bcc517c956a7ac979815cd", // transaction hash
		"given": "20000", // proposed amount [from -> to]
		"received": "20000" // proposed amount [from <- to]
	},
	// TrustlineUpdate
	{
		"networkAddress": "0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9",
		"blockNumber": 6997899,
		"timestamp": 1524655600,
		"type": "TrustlineUpdate",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x10d4e9acb58d42d433dbc5c995e9a258cd2bb7fe82fedf2ebab82e450d30c643",
		"given": "10000", // accepted amount [from -> to]
		"received": "10000" // accepted amount [from <- to]
	},
	// Transfer	
	{
		"networkAddress": "0xC0B33D88C704455075a0724AA167a286da778DDE",
		"blockNumber": 7011809,
		"timestamp": 1524755036,
		"type": "Transfer",
		"from": "0xcbF1153F6e5AC01D363d432e24112e8aA56c55ce",
		"to": "0x7Ec3543702FA8F2C7b2bD84C034aAc36C263cA8b",
		"status": "confirmed",
		"transactionId": "0x05c91f6506e78b1ca2413df9985ca7d37d2da5fc076c0b55c5d9eb9fdd7513a6",
		"amount": "100" // transferred amount
	},
	... // more event objects
]
```

---

### Transaction infos of user
### `/users/:user/txinfos`
Returns information that is needed to sign a transaction.
#### Request
```
GET /users/:user/txinfos
```
#### Parameters
|Name|Type|Required|Description|
|-|-|-|-|
|user|string|YES|Address of user|
|type|string|NO|Either `TrustlineUpdate`, `TrustlineUpdateRequest` or `Transfer`|
|fromBlock|int|NO|Start of block range|
#### Response
```javascript
{
  "gasPrice": 0,
  "balance": 2377634165348042492, // ETH balance of user in wei
  "nonce": 58
}
```

---

### Latest block number
### `/blocknumber`
Returns the latest block number.
#### Request
```
GET /blocknumber
```
#### Response
```javascript
7426584 // latest block number
```

---

### Relay
### `/relay`
Relays a raw transaction to the blockchain.
#### Request
```
POST /relay
```
#### POST body
|Name|Type|Required|Description|
|-|-|-|-|
|rawTransaction|string|YES|signed transation|
#### Response
```javascript
'0x...' // hash of transaction if relayed successfully
```