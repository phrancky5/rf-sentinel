"""Lightweight 1D CNN for IQ modulation classification."""

import torch.nn as nn

from .features import N_CHANNELS

ML_CLASSES = (
    "fm",       # Wideband FM broadcast
    "am",       # AM-DSB broadcast
    "ssb",      # Single sideband (USB/LSB)
    "cw",       # Morse code (OOK carrier)
    "nfm",      # Narrowband FM voice
    "lora",     # LoRa chirp spread spectrum
    "pocsag",   # Pager (2FSK)
    "digital",  # Generic digital (PSK/QAM/OFDM)
    "noise",    # No signal
)
N_CLASSES = len(ML_CLASSES)


class SignalCNN(nn.Module):
    """1D CNN on IQ-derived features.

    Input:  (batch, 12, 1024) — see features.py for channel layout
    Output: (batch, N_CLASSES) logits
    """

    def __init__(self, dropout: float = 0.3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(N_CHANNELS, 128, kernel_size=7, stride=2, padding=3),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout1d(dropout),
            nn.Conv1d(128, 128, kernel_size=5, stride=2, padding=2),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout1d(dropout),
            nn.Conv1d(128, 128, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout1d(dropout),
            nn.Conv1d(128, 128, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout1d(dropout),
            nn.Conv1d(128, 128, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(128),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(128, N_CLASSES),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x).squeeze(-1)
        return self.head(x)
