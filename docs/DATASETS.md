# NetPulse Datasets

This document details the provenance, licensing, and schema mappings of the primary datasets used by NetPulse to drive the ML engine.

## 1. RIPE Atlas
* **Description**: Active measurement network consisting of over 12,000 global hardware and software probes. Used to gather real-time latency and packet loss data (ping/traceroute).
* **URL**: [https://atlas.ripe.net/api/v2/](https://atlas.ripe.net/api/v2/)
* **License/Usage Terms**: Public data is free to access. To create custom measurements, Atlas Credits are required. Our MVP strictly utilizes existing public, continuous measurements.
* **Refresh Cadence**: Continuous (streaming/polling).
* **Fields Used**: `prb_id`, `timestamp`, `min` (RTT), `error`
* **Known Limitations**: Some probes go offline silently. Measurement IDs might be paused or stopped by their owners.
* **Sample Record**:
  ```json
  {
      "fw": 5080,
      "mver": "2.2.1",
      "lts": 19,
      "dst_name": "193.0.14.129",
      "af": 4,
      "dst_addr": "193.0.14.129",
      "src_addr": "192.168.1.100",
      "proto": "ICMP",
      "ttl": 58,
      "size": 48,
      "result": [{"rtt": 12.3}],
      "rcvd": 1,
      "sent": 1,
      "min": 12.3,
      "max": 12.3,
      "avg": 12.3,
      "msm_id": 1030,
      "prb_id": 1001,
      "timestamp": 1704067200
  }
  ```

## 2. RouteViews
* **Description**: Archive of BGP routing tables (RIBs) and BGP update messages collected from vantage points globally. Provided by the University of Oregon.
* **URL**: [http://archive.routeviews.org/bgpdata/](http://archive.routeviews.org/bgpdata/)
* **License/Usage Terms**: Public domain / free for research use.
* **Refresh Cadence**: Updates available every 15 minutes; RIBs available every 2 hours.
* **Fields Used**: `peer_as`, `prefix`, `as_path`, `bgp_message.type`
* **Known Limitations**: Historical data requires fetching and parsing large MRT files (`.bz2`). Update streams have a 15-minute delay from real time.
* **Sample Record** (Extracted from MRT):
  ```json
  {
      "peer_as": 3333,
      "bgp_message": {
          "type": 2, 
          "nlri": [{"prefix": "192.0.2.0", "length": 24}],
          "path_attributes": [{"type": 2, "value": [3333, 4444, 5555]}]
      }
  }
  ```

## 3. RIPE RIS
* **Description**: RIPE Routing Information Service. Collects and stores BGP routing information. Provides both raw MRT dumps and a live WebSocket stream (RIS Live).
* **URL**: [https://data.ris.ripe.net/](https://data.ris.ripe.net/)
* **License/Usage Terms**: Public data provided by RIPE NCC. Free for research.
* **Refresh Cadence**: Live via WebSockets, or historical updates every 5 minutes.
* **Fields Used**: `peer_asn`, `path`, `announcements`, `withdrawals`
* **Known Limitations**: `mrtparse` in Python is relatively slow; for high throughput, Rust-based parsers or the RIS Live WebSocket stream are necessary.

## 4. CAIDA AS Relationships
* **Description**: The CAIDA AS Relationships Dataset provides a graph of inferred business relationships between Autonomous Systems (provider-customer, peer-peer).
* **URL**: [https://data.caida.org/datasets/as-relationships/](https://data.caida.org/datasets/as-relationships/)
* **License/Usage Terms**: Free for research/education use. **Citation required**: *"The CAIDA AS Relationships Dataset, <date>"*
* **Refresh Cadence**: Monthly.
* **Fields Used**: `<provider-as>`, `<customer-as>`, `relationship_type (-1 or 0)`
* **Known Limitations**: Inferred data (not ground truth), meaning some peering links, especially at IXPs, may be missing or misclassified.
* **Sample Record**:
  ```text
  # format:provider-as|customer-as|-1
  1|11537|-1|bgp
  1|21673|-1|bgp
  # format:peer-as|peer-as|0
  1|115|0|bgp
  ```

## 5. Cloudflare Radar
* **Description**: Aggregated Internet traffic and outage data from Cloudflare's global network edge. Used as a corroboration signal for incidents.
* **URL**: [https://radar.cloudflare.com/](https://radar.cloudflare.com/)
* **License/Usage Terms**: Cloudflare, Inc. (CC BY-NC 4.0).
* **Refresh Cadence**: Polled via API.
* **Fields Used**: Outage signals, traffic anomalies.
