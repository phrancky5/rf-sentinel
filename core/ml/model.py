"""Lightweight 1D CNN for IQ modulation classification."""

import torch.nn as nn

ML_CLASSES = ("fm", "am", "nfm", "digital", "noise")
N_CLASSES = len(ML_CLASSES)


class SignalCNN(nn.Module):
    """1D CNN on I/Q + power spectrum.

    Input:  (batch, 3, 4096)  — I, Q, log-magnitude spectrum
    Output: (batch, 5) logits
    """

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Conv1d(64, 64, kernel_size=5, stride=2, padding=2),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Conv1d(64, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Conv1d(64, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(64),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Linear(64, N_CLASSES)

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x).squeeze(-1)
        return self.head(x)
