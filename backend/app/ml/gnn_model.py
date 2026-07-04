import torch
import torch.nn as nn
import torch.nn.functional as F

class GraphConv(nn.Module):
    """
    Pure PyTorch implementation of a Graph Convolution Layer.
    Computes: X' = A_norm * X * W
    """
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.weight = nn.Parameter(torch.Tensor(in_features, out_features))
        self.bias = nn.Parameter(torch.Tensor(out_features))
        self.reset_parameters()
        
    def reset_parameters(self):
        nn.init.xavier_uniform_(self.weight)
        nn.init.zeros_(self.bias)
        
    def forward(self, x: torch.Tensor, adj: torch.sparse.Tensor) -> torch.Tensor:
        # X * W
        support = torch.mm(x, self.weight)
        # A * (X * W)
        out = torch.sparse.mm(adj, support)
        return out + self.bias

class TemporalGNN(nn.Module):
    """
    GConvGRU equivalent: Integrates graph convolutions with temporal recurrence.
    Captures both spatial (topology) and temporal (history) signals.
    """
    def __init__(self, node_features: int, hidden_dim: int = 16):
        super().__init__()
        
        # Spatial feature extraction
        self.conv1 = GraphConv(node_features, hidden_dim)
        
        # Temporal memory
        self.gru = nn.GRU(input_size=hidden_dim, hidden_size=hidden_dim, batch_first=True)
        
        # Prediction head (per-node instability score 0.0 - 1.0)
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x_seq: torch.Tensor, adj: torch.sparse.Tensor) -> torch.Tensor:
        """
        x_seq: [seq_len, num_nodes, node_features]
        Returns: [num_nodes, 1] probability vector for the next time step.
        """
        seq_len = x_seq.size(0)
        num_nodes = x_seq.size(1)
        
        # Apply GCN independently to each snapshot
        # shape: [seq_len, num_nodes, hidden_dim]
        gcn_out = []
        for t in range(seq_len):
            h_t = F.relu(self.conv1(x_seq[t], adj))
            gcn_out.append(h_t)
            
        gcn_out = torch.stack(gcn_out) # [S, N, H]
        
        # To run GRU per-node, we transpose to treat nodes as the batch dimension
        # shape: [num_nodes, seq_len, hidden_dim]
        gru_in = gcn_out.transpose(0, 1)
        
        # output is the final hidden state for each node
        _, h_n = self.gru(gru_in) # h_n shape: [1, num_nodes, hidden_dim]
        
        # Final prediction
        out = self.fc(h_n.squeeze(0)) # [num_nodes, 1]
        return torch.sigmoid(out).squeeze(-1)
