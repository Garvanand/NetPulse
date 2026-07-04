import torch
import torch.nn as nn

class LatencyForecaster(nn.Module):
    """
    A lightweight univariate time-series forecaster for per-probe latency.
    Uses a standard LSTM architecture.
    """
    def __init__(self, hidden_dim: int = 32, num_layers: int = 2):
        super().__init__()
        
        self.lstm = nn.LSTM(
            input_size=1, 
            hidden_size=hidden_dim, 
            num_layers=num_layers, 
            batch_first=True
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: [batch_size, seq_len, 1] (historical RTT sequence)
        Returns: [batch_size, 1] (predicted RTT for next step)
        """
        # We only care about the final hidden state for prediction
        _, (h_n, _) = self.lstm(x)
        
        # h_n shape: [num_layers, batch_size, hidden_dim]
        # Take the top layer
        top_h = h_n[-1]
        
        out = self.fc(top_h)
        return out
