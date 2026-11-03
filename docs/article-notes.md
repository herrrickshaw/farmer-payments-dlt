# Notes on Deshmukh & Patil (2022)

Sagar Deshmukh & Sharvari Patil, "Applications and Challenges of Blockchain Technology in
Agriculture Sector: A Review", *Journal of Agricultural Extension Management* XXIII(1), 2022,
pp. 159–176 (NIAM / MANAGE, Hyderabad). Read in full from the supplied PDF.

## Core claims relevant to payments

- Blockchain is a DLT with immutable cryptographic records; permissioned/permissionless and
  public/private/consortium structures (p.163). Consortium = rights limited to selected nodes.
- It "allows widespread financial transactions between underutilized groups, without the need for
  intermediaries such as banks" (p.163, citing Mehta et al. 2021).
- **AgriDigital** (Dec 2016): first settlement of a grain sale on a blockchain (23.46 tons);
  later >1,300 users, >1.6 Mt grain, ~US$360M in grower payments (p.166, citing ICT4Ag 2017 and
  Chang et al. 2019). This is the article's strongest direct farmer-payment example.
- **e-NAM / APMC mandis**: Goundar (2020) found arrival/bidding price variation vs Agmarknet in
  three UP APMCs and proposed blockchain + smart contracts for transparent, rule-enforcing
  transactions (pp.165–166).
- **Smart contracts** for contract-farming disputes (p.168–169); **temporary labour contracts** and
  fair payment/tax control (p.169).
- **Certification/documentation and land records**: farmers lose time and money assembling RoR,
  mutation extract, crop certificate for loans/subsidies (pp.169–171) — the identity/eligibility
  layer any scheme payment depends on.
- FPOs: 10,000 FPO programme (2019-20 budget); blockchain relevant to input procurement, inventory,
  transaction records, financial statements, insurance (p.173). Indian startups named: Samudra
  Network, Kultivate, TRST01, TraceX, My Crop (seed traceability).

## Challenges listed (pp.171–172) and how this repo responds

| Article challenge | Response in this repo |
|---|---|
| Regulation | Keep fiat settlement on regulated rails; ledger is a record, not a currency |
| Digital gap / expertise | Farmer never touches keys; FPO/agency/bank nodes act on their behalf |
| Privacy / lost private keys | Org-held keys, recoverable by consortium governance; no personal data on-chain (hashes/IDs only) |
| Low transaction speed (Bitcoin ~10 min) | Permissioned consortium chain, not PoW |
| Storage growth | Store hashes on-ledger, documents off-ledger |
| Energy/hardware | No mining in permissioned designs |
| High cost for SMEs | Shared consortium infrastructure run by FPO federations/banks |

## Caveats on the article itself

- It is a narrative review; the payment content is a few paragraphs and the market-growth figure
  (US$45M in 2018 → US$3,314.6M by 2023) is a vendor-style forecast, not evidence of impact.
- Some references are web pages/blogs (Investopedia, Reuters, startup directories).
- It reports no outcome data for farmer income or cost savings from any payment pilot.
