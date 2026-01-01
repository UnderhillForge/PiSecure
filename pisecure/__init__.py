"""
PiSecure - Decentralized Security Framework for Raspberry Pi
=============================================================

A comprehensive blockchain security platform designed specifically for
Raspberry Pi devices, providing decentralized security, hardware-verified
mining, and secure communication protocols.
"""

__version__ = "0.1.0"
__author__ = "J Stekervetz"
__email__ = "mr_underhill@icloud.com"

from .core import SignChain, HardwareVerifier, SignTokenMiner

__all__ = [
    'SignChain',
    'HardwareVerifier',
    'SignTokenMiner',
    '__version__'
]