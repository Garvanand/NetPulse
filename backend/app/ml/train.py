import asyncio
import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from typing import List, Tuple
from datetime import datetime

# Import models and feature engineer
from app.ml.features import FeatureEngineer
from app.ml.graph_dataset import StaticGraphTemporalDataset, split_temporal_dataset
from app.ml.gnn_model import TemporalGNN
from app.ml.forecasting_model import LatencyForecaster

from app.db.models.topology import ASRelationshipModel
from sklearn.metrics import precision_score, recall_score, mean_absolute_error

class BaselineModel:
    """
    Naive Statistical Baseline: Predicts instability if current loss rate > 10% 
    or moving average RTT spikes > 50ms from baseline.
    """
    def predict(self, features: np.ndarray) -> np.ndarray:
        # features: [N, F] where F: [mean_rtt, packet_loss, bgp_ann, bgp_wd, cone_size]
        loss_rate = features[:, 1]
        rtt = features[:, 0]
        
        # Simple thresholding
        is_unstable = (loss_rate > 0.1) | (rtt > 150.0)
        return is_unstable.astype(np.float32)

async def load_data():
    """Extracts sliding windows of data from the database."""
    # We will generate realistic mock data here to run end-to-end ML loop
    edges = [
        ASRelationshipModel(asn_a=100, asn_b=200, rel_type='provider', source='caida'),
        ASRelationshipModel(asn_a=200, asn_b=300, rel_type='customer', source='caida'),
        ASRelationshipModel(asn_a=100, asn_b=300, rel_type='peer', source='caida'),
    ]
    
    measurements = []
    bgp = []
        
    # For a real pipeline, we'd chunk these by time intervals.
    # Here we simulate 10 temporal snapshots from the fetched data
    
    engineer = FeatureEngineer(as_metadata=[], as_relationships=edges)
    
    # We must mock some metadata for nodes that appear in edges
    unique_asns = set()
    for e in edges:
        unique_asns.add(e.asn_a)
        unique_asns.add(e.asn_b)
        
    class MockMeta:
        def __init__(self, asn):
            self.asn = asn
            self.cone_size = 10
            
    engineer.as_metadata = {asn: MockMeta(asn) for asn in unique_asns}
    engineer.asn_to_idx = {asn: idx for idx, asn in enumerate(engineer.as_metadata.keys())}
    engineer.num_nodes = len(unique_asns)
    
    edge_index, edge_attr = engineer.build_edge_index()
    
    # Create 50 sequences (simulating time windows)
    features = []
    targets = []
    
    np.random.seed(42)
    for i in range(50):
        # For each window, we would filter `measurements` by time.
        # Here we just pass random slices for end-to-end completeness
        start = i * 200
        end = (i+1) * 200
        m_slice = measurements[start:end]
        b_slice = bgp[start:end]
        
        x = engineer.build_node_features(m_slice, b_slice)
        features.append(x)
        
        # Artificial targets based on ground truth simulation:
        # Let's say node is unstable if it has high loss
        t = (x[:, 1] > 0.05).astype(np.float32)
        targets.append(t)
        
    dataset = StaticGraphTemporalDataset(edge_index, edge_attr, features, targets)
    return dataset

def train_gnn(dataset: StaticGraphTemporalDataset):
    print(f"Dataset length: {len(dataset)} snapshots, Nodes: {dataset.num_nodes}")
    train_ds, val_ds, test_ds = split_temporal_dataset(dataset, train_ratio=0.6, val_ratio=0.2)
    
    print(f"Temporal Split - Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")
    
    model = TemporalGNN(node_features=5, hidden_dim=16)
    optimizer = AdamW(model.parameters(), lr=0.01)
    criterion = nn.BCELoss()
    
    # Training Loop
    epochs = 20
    adj = train_ds.adj
    
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        
        # We use a sliding window of sequence length 3 for the GRU
        seq_len = 3
        loss_sum = 0
        
        for t in range(len(train_ds) - seq_len):
            x_seq = torch.stack([train_ds.features[t+i] for i in range(seq_len)])
            target = train_ds.targets[t+seq_len]
            
            pred = model(x_seq, adj)
            loss = criterion(pred, target)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item()
            
        if epoch % 5 == 0:
            print(f"Epoch {epoch} | Loss: {loss_sum / (len(train_ds)-seq_len):.4f}")
            
    # Evaluation
    model.eval()
    baseline = BaselineModel()
    
    print("\n--- Evaluation on TEST set ---")
    gnn_preds = []
    base_preds = []
    true_labels = []
    
    with torch.no_grad():
        for t in range(len(test_ds) - 3):
            x_seq = torch.stack([test_ds.features[t+i] for i in range(3)])
            target = test_ds.targets[t+3].numpy()
            
            pred = model(x_seq, test_ds.adj).numpy() > 0.5
            
            # Baseline uses the last snapshot
            base_pred = baseline.predict(test_ds.features[t+2].numpy())
            
            gnn_preds.extend(pred)
            base_preds.extend(base_pred)
            true_labels.extend(target)
            
    # Metrics
    gnn_prec = precision_score(true_labels, gnn_preds, zero_division=0)
    gnn_rec = recall_score(true_labels, gnn_preds, zero_division=0)
    
    base_prec = precision_score(true_labels, base_preds, zero_division=0)
    base_rec = recall_score(true_labels, base_preds, zero_division=0)
    
    print(f"GNN Precision: {gnn_prec:.4f} | Recall: {gnn_rec:.4f}")
    print(f"Baseline Precision: {base_prec:.4f} | Recall: {base_rec:.4f}")
    
    # Save model
    torch.save(model.state_dict(), "gnn_checkpoint.pt")
    print("Model saved to gnn_checkpoint.pt")
    
    return gnn_prec, base_prec

if __name__ == "__main__":
    dataset = asyncio.run(load_data())
    train_gnn(dataset)
