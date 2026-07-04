# NetPulse Roadmap

The following outlines the intended future expansion for NetPulse beyond Phase 15.

## Q3 2026: Scale & Coverage
- **Kafka Ingestion Pipeline**: Migrate the single-process `asyncio` ingestion loops to a distributed Apache Kafka topic architecture to handle 10x the BGP event volume without lagging.
- **Enhanced ML Edge Dynamics**: Upgrade the Temporal GNN to support dynamic edge weight updates in real-time based on BGP withdrawals, rather than relying on daily static CAIDA snapshots.

## Q4 2026: Actionability & Deep Inspection
- **Active Looking Glass Integration**: Instead of purely relying on passive BGP dumps, integrate automated API queries against public BGP Looking Glasses to verify route propagation issues dynamically.
- **Synthetic Probe Deployments**: Support bringing-your-own-probe (BYOP) to allow enterprise users to deploy their own active measurement agents on their edge networks, feeding private data into their siloed GNN instance.
- **Automated Remediation Webhooks**: Allow users to configure webhook endpoints that trigger automatically when a predictive incident reaches `CRITICAL` severity, enabling automated BGP failover in their local routing infrastructure.
