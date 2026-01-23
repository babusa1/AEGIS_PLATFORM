"""
Device/Wearable Connector

Ingests data from health devices and wearables:
- Apple HealthKit
- Google Fit
- Fitbit
- Garmin
- Withings
"""

from aegis_connectors.devices.connector import DeviceConnector
from aegis_connectors.devices.healthkit import HealthKitAdapter
from aegis_connectors.devices.googlefit import GoogleFitAdapter
from aegis_connectors.devices.fitbit import FitbitAdapter

__all__ = [
    "DeviceConnector",
    "HealthKitAdapter",
    "GoogleFitAdapter",
    "FitbitAdapter",
]
