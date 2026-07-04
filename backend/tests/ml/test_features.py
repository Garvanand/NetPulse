import numpy as np
from app.ml.features import FeatureEngineer
from app.db.models.topology import ASRelationshipModel

class MockMeasurement:
    def __init__(self, asn_src, rtt_ms, packet_loss):
        self.asn_src = asn_src
        self.rtt_ms = rtt_ms
        self.packet_loss = packet_loss

class MockBGPEvent:
    def __init__(self, origin_asn, event_type):
        self.origin_asn = origin_asn
        self.event_type = event_type

class MockMeta:
    def __init__(self, asn, cone_size):
        self.asn = asn
        self.cone_size = cone_size

def test_feature_engineer():
    metadata = [
        MockMeta(100, 10),
        MockMeta(200, 100),
    ]
    
    # 100 provides to 200
    edges = [
        ASRelationshipModel(asn_a=100, asn_b=200, rel_type='provider', source='caida'),
    ]
    
    engineer = FeatureEngineer(metadata, edges)
    assert engineer.num_nodes == 2
    
    edge_index, edge_attr = engineer.build_edge_index()
    assert edge_index.shape == (2, 1)
    assert edge_index[0, 0] == engineer.asn_to_idx[100]
    assert edge_index[1, 0] == engineer.asn_to_idx[200]
    
    # One-hot provider
    assert edge_attr[0, 0] == 1.0
    
    measurements = [
        MockMeasurement(100, 50.0, 0.0),
        MockMeasurement(100, 60.0, 0.1),
    ]
    
    bgp_events = [
        MockBGPEvent(200, 'announce'),
        MockBGPEvent(200, 'withdraw'),
        MockBGPEvent(200, 'withdraw'),
    ]
    
    x = engineer.build_node_features(measurements, bgp_events)
    
    idx_100 = engineer.asn_to_idx[100]
    idx_200 = engineer.asn_to_idx[200]
    
    # Node 100: mean_rtt = 55.0, loss = 0.05
    assert np.isclose(x[idx_100, 0], 55.0)
    assert np.isclose(x[idx_100, 1], 0.05)
    
    # Node 200: bgp = 1 announce, 2 withdraws
    assert x[idx_200, 2] == 1.0
    assert x[idx_200, 3] == 2.0
