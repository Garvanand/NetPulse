import torch
from typing import List, Tuple
import numpy as np

class StaticGraphTemporalDataset:
    """
    A lightweight, pure-PyTorch implementation equivalent to PyG Temporal's
    StaticGraphTemporalSignal.
    
    It holds a static graph structure (edge_index, edge_weight) and 
    a sequence of node features over time.
    """
    
    def __init__(
        self,
        edge_index: np.ndarray,
        edge_weight: np.ndarray,
        features: List[np.ndarray],
        targets: List[np.ndarray],
    ):
        """
        edge_index: [2, num_edges]
        edge_weight: [num_edges, num_edge_features]
        features: List of [num_nodes, num_node_features] arrays over time T
        targets: List of [num_nodes] target arrays (e.g., instability labels) over time T
        """
        self.edge_index = torch.tensor(edge_index, dtype=torch.long)
        # For simplicity in pure PT, we'll just use the first edge feature as a scalar weight,
        # or uniform weights if multi-dimensional.
        if edge_weight.ndim > 1 and edge_weight.shape[1] > 0:
            self.edge_weight = torch.tensor(edge_weight[:, 0], dtype=torch.float)
        else:
            self.edge_weight = torch.ones(edge_index.shape[1], dtype=torch.float)
            
        self.features = [torch.tensor(f, dtype=torch.float) for f in features]
        self.targets = [torch.tensor(t, dtype=torch.float) for t in targets]
        self.num_nodes = features[0].shape[0] if features else 0
        
        # Build the sparse adjacency matrix once
        # Add self-loops
        loops = torch.arange(0, self.num_nodes, dtype=torch.long).unsqueeze(0).repeat(2, 1)
        loop_weights = torch.ones(self.num_nodes, dtype=torch.float)
        
        full_edge_index = torch.cat([self.edge_index, loops], dim=1)
        full_edge_weight = torch.cat([self.edge_weight, loop_weights], dim=0)
        
        # Degree normalization: D^{-0.5} A D^{-0.5}
        deg = torch.zeros(self.num_nodes, dtype=torch.float)
        deg.scatter_add_(0, full_edge_index[0], full_edge_weight)
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt.masked_fill_(deg_inv_sqrt == float('inf'), 0)
        
        norm_weight = deg_inv_sqrt[full_edge_index[0]] * full_edge_weight * deg_inv_sqrt[full_edge_index[1]]
        
        self.adj = torch.sparse_coo_tensor(
            full_edge_index, norm_weight, (self.num_nodes, self.num_nodes)
        )
        
    def __len__(self):
        return len(self.features)
        
    def get_snapshot(self, t: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[t], self.targets[t]

def split_temporal_dataset(dataset: StaticGraphTemporalDataset, train_ratio=0.7, val_ratio=0.15) -> Tuple[StaticGraphTemporalDataset, StaticGraphTemporalDataset, StaticGraphTemporalDataset]:
    """
    STRICT Temporal split. No random shuffling to prevent data leakage.
    Returns (train_dataset, val_dataset, test_dataset)
    """
    T = len(dataset)
    if T == 0:
        return dataset, dataset, dataset
        
    train_end = int(T * train_ratio)
    val_end = int(T * (train_ratio + val_ratio))
    
    # Extract original numpy arrays to recreate subsets
    edge_index = dataset.edge_index.numpy()
    edge_weight = dataset.edge_weight.unsqueeze(-1).numpy()
    
    train_feat = [f.numpy() for f in dataset.features[:train_end]]
    train_targ = [t.numpy() for t in dataset.targets[:train_end]]
    
    val_feat = [f.numpy() for f in dataset.features[train_end:val_end]]
    val_targ = [t.numpy() for t in dataset.targets[train_end:val_end]]
    
    test_feat = [f.numpy() for f in dataset.features[val_end:]]
    test_targ = [t.numpy() for t in dataset.targets[val_end:]]
    
    train_ds = StaticGraphTemporalDataset(edge_index, edge_weight, train_feat, train_targ)
    val_ds = StaticGraphTemporalDataset(edge_index, edge_weight, val_feat, val_targ)
    test_ds = StaticGraphTemporalDataset(edge_index, edge_weight, test_feat, test_targ)
    
    return train_ds, val_ds, test_ds
