"""1D CNN with residual blocks and channel attention for IQ classification."""

import torch
import torch.nn as nn

from .features import N_CHANNELS

ML_CLASSES = (
    "fm",       # Wideband FM broadcast
    "am",       # AM-DSB broadcast (airband)
    "nfm",      # Narrowband FM voice
    "ofdm",     # Multi-carrier digital (DAB+, DVB-T, WiFi)
    "tdma",     # Bursty single-carrier digital (TETRA, DMR, GSM)
    "lora",     # LoRa chirp spread spectrum
    "adsb",     # ADS-B pulsed (1090 MHz)
    "noise",    # No signal
)
N_CLASSES = len(ML_CLASSES)


class _SE(nn.Module):
    """Squeeze-and-Excitation channel attention."""

    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction),
            nn.ReLU(),
            nn.Linear(channels // reduction, channels),
            nn.Sigmoid(),
        )

    def forward(self, x):
        # x: (B, C, L)
        w = x.mean(dim=2)          # (B, C)
        w = self.fc(w).unsqueeze(2) # (B, C, 1)
        return x * w


class _ResBlock(nn.Module):
    """Conv1d residual block with SE attention."""

    def __init__(self, channels: int, kernel_size: int, stride: int, dropout: float):
        super().__init__()
        pad = kernel_size // 2
        self.conv = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size, stride=stride, padding=pad),
            nn.ReLU(),
            nn.BatchNorm1d(channels),
            nn.Dropout1d(dropout),
            nn.Conv1d(channels, channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(channels),
        )
        self.se = _SE(channels)
        self.downsample = nn.AvgPool1d(stride) if stride > 1 else nn.Identity()
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = self.downsample(x)
        out = self.conv(x)
        out = self.se(out)
        return self.relu(out + residual)


class SignalCNN(nn.Module):
    """1D CNN with residual blocks and SE attention.

    Input:  (batch, N_CHANNELS, 1024)
    Output: (batch, N_CLASSES) logits
    """

    def __init__(self, dropout: float = 0.3):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(N_CHANNELS, 128, kernel_size=7, stride=2, padding=3),
            nn.ReLU(),
            nn.BatchNorm1d(128),
        )
        self.blocks = nn.Sequential(
            _ResBlock(128, kernel_size=5, stride=2, dropout=dropout),
            _ResBlock(128, kernel_size=3, stride=2, dropout=dropout),
            _ResBlock(128, kernel_size=3, stride=2, dropout=dropout),
            _ResBlock(128, kernel_size=3, stride=2, dropout=dropout),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(128, N_CLASSES),
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.pool(x).squeeze(-1)
        return self.head(x)
