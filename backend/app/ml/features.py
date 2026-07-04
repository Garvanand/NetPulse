import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

class FeatureEngineer:
    """
    Constructs node features and edge indices for the Temporal GNN
    from the raw NetPulse database models.
    """
    
    def __init__(self, as_metadata: list, as_relationships: list):
        self.as_metadata = {m.asn: m for m in as_metadata}
        self.as_relationships = as_relationships
        
        # Build ASN to index mapping for the GNN
        self.asn_to_idx = {asn: idx for idx, asn in enumerate(self.as_metadata.keys())}
        self.idx_to_asn = {idx: asn for asn, idx in self.asn_to_idx.items()}
        self.num_nodes = len(self.asn_to_idx)
        
    def build_edge_index(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Builds the COO format edge index and edge attributes for the GNN.
        Returns:
            edge_index: shape [2, num_edges]
            edge_attr: shape [num_edges, 3] (One-hot encoded relation types)
        """
        edges = []
        attrs = []
        
        for rel in self.as_relationships:
            if rel.asn_a in self.asn_to_idx and rel.asn_b in self.asn_to_idx:
                u = self.asn_to_idx[rel.asn_a]
                v = self.asn_to_idx[rel.asn_b]
                
                edges.append([u, v])
                
                # One-hot: [is_provider, is_peer, is_customer]
                if rel.rel_type == 'provider':
                    attrs.append([1.0, 0.0, 0.0])
                elif rel.rel_type == 'peer':
                    attrs.append([0.0, 1.0, 0.0])
                elif rel.rel_type == 'customer':
                    attrs.append([0.0, 0.0, 1.0])
                else:
                    attrs.append([0.0, 0.0, 0.0])
                    
        if not edges:
            return np.empty((2, 0), dtype=np.int64), np.empty((0, 3), dtype=np.float32)
            
        edge_index = np.array(edges).T # [2, E]
        edge_attr = np.array(attrs, dtype=np.float32)
        
        return edge_index, edge_attr

    def build_node_features(self, measurements: list, bgp_events: list) -> np.ndarray:
        """
        Builds the N x F feature matrix for a specific time window.
        Features: [mean_rtt, packet_loss, bgp_announces, bgp_withdraws, log_cone_size]
        """
        F = 5
        x = np.zeros((self.num_nodes, F), dtype=np.float32)
        
        # Static feature: log_cone_size
        for asn, m in self.as_metadata.items():
            idx = self.asn_to_idx[asn]
            x[idx, 4] = np.log10((m.cone_size or 0) + 1)
            
        # Accumulators
        rtt_sums = defaultdict(float)
        rtt_counts = defaultdict(int)
        loss_sums = defaultdict(float)
        loss_counts = defaultdict(int)
        
        for m in measurements:
            asn = m.asn_src
            if asn in self.asn_to_idx:
                idx = self.asn_to_idx[asn]
                if m.rtt_ms is not None:
                    rtt_sums[idx] += m.rtt_ms
                    rtt_counts[idx] += 1
                if m.packet_loss is not None:
                    loss_sums[idx] += m.packet_loss
                    loss_counts[idx] += 1
                    
        for e in bgp_events:
            asn = e.origin_asn
            if asn in self.asn_to_idx:
                idx = self.asn_to_idx[asn]
                if e.event_type == 'announce':
                    x[idx, 2] += 1.0
                elif e.event_type == 'withdraw':
                    x[idx, 3] += 1.0
                    
        # Averages
        for idx in range(self.num_nodes):
            if rtt_counts[idx] > 0:
                x[idx, 0] = rtt_sums[idx] / rtt_counts[idx]
            else:
                x[idx, 0] = 0.0 # Imputation logic could be better
                
            if loss_counts[idx] > 0:
                x[idx, 1] = loss_sums[idx] / loss_counts[idx]
            else:
                x[idx, 1] = 0.0
                
        return x
