import torch
from torch import nn

def get_device(force_cpu):
    if torch.cuda.is_available() and not force_cpu:
        print('Using GPU.')
        return torch.device('cuda')
    else:
        print('Using CPU.')
        return torch.device('cpu')

class Model(nn.Module):
    def _init_weights(self, m):
        if type(m) == nn.Linear:
            nn.init.xavier_uniform_(m.weight)

    def __init__(
        self,
        embed_dim,
        hid_dim,
        out_dim,
        lstm_layers,
        dropout,
        win_rad,
        voc_len
    ):
        super().__init__()
        self.win_rad = win_rad
        # self.in_drop = nn.Dropout(0.1)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hid_dim,
            num_layers=lstm_layers,
            bidirectional=True,
            batch_first=True
        )
        self.mlp = nn.Sequential(
            nn.Linear(hid_dim * 2 + embed_dim, hid_dim),
            nn.Dropout(dropout),
            nn.LeakyReLU(),
            nn.Linear(hid_dim, out_dim),
            nn.Dropout(dropout), #??
            nn.LeakyReLU(),
            nn.Linear(out_dim, voc_len, bias=False)
        )
        self.mlp.apply(self._init_weights)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        lr_ctx = lstm_out[:,self.win_rad,:]
        # t_emb = x[:,self.win_rad,:]
        # ctx = torch.cat((lr_ctx, t_emb), 1)
        scores = self.mlp(lr_ctx)

        return scores
