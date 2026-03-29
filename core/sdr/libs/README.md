# HackRF Native Libraries (Windows)

These DLLs are required by the `pyhackrf2` Python package on Windows.
They are loaded automatically by `hackrf_device.py` at runtime.

| File             | Source                         | Purpose                        |
|------------------|--------------------------------|--------------------------------|
| hackrf.dll       | HackRF / libhackrf project     | HackRF One hardware interface  |
| libusb-1.0.dll   | libusb project                 | USB communication layer        |
| pthreadVC2.dll   | pthreads-win32                 | POSIX threading for Windows    |

## Where to get these DLLs

If the DLLs are not included (e.g. excluded by `.gitignore`), copy them
from any of these sources:

1. **PothosSDR** — `C:\Program Files\PothosSDR\bin\`
2. **HackRF release** — https://github.com/greatscottgadgets/hackrf/releases
   (extract `hackrf-<version>-windows.zip`, DLLs are in `bin/`)
3. **SDRangel** — `C:\Program Files\SDRangel\`

Place all three DLLs in this folder (`core/sdr/libs/`).
