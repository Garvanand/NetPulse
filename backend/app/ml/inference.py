import torch
import numpy as np
from app.ml.gnn_model import TemporalGNN
from app.ml.features import FeatureEngineer

class NetPulseInference:
    def __init__(self, model_path: str, engineer: FeatureEngineer):
        self.engineer = engineer
        self.model = TemporalGNN(node_features=5, hidden_dim=16)
        self.model.load_state_dict(torch.load(model_path))
        self.model.eval()
        
    async def predict_instability(self, recent_measurements: list, recent_bgp: list, adj: torch.sparse.Tensor):
        """
        Runs inference on the latest 3 time windows.
        Returns a dictionary of ASN -> prediction score.
        """
        # In a real deployed environment, we would maintain a rolling buffer of 
        # the last 3 time windows. For this inference signature, we compute the current
        # snapshot and duplicate it (naive approach for a cold start) or take the history.
        
        # We will just take the single snapshot and duplicate it for the sequence 
        # to satisfy the GRU dimension requirement.
        curr_feat = self.engineer.build_node_features(recent_measurements, recent_bgp)
        curr_tensor = torch.tensor(curr_feat, dtype=torch.float)
        
        # [seq_len=3, num_nodes, features]
        x_seq = torch.stack([curr_tensor, curr_tensor, curr_tensor])
        
        import asyncio
        
        def _forward_pass():
            with torch.no_grad():
                return self.model(x_seq, adj).numpy()
        
        preds = await asyncio.to_thread(_forward_pass)
            
        results = {}
        for idx, score in enumerate(preds):
            asn = self.engineer.idx_to_asn[idx]
            results[asn] = float(score)
            
        return results
