import torch
import torch.nn as nn

class GRUModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
        super(GRUModel, self).__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.gru(x)
        out = out[:, -1, :]          # last timestep
        out = self.fc(out)
        return out


def predict_with_gru(model, X_tensor, device="cpu"):
    model.eval()
    with torch.no_grad():
        X_tensor = X_tensor.to(device)
        output = model(X_tensor)
    return output.cpu().numpy().tolist()
