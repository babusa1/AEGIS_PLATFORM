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
from aegis_connectors.devices.garmin import GarminAdapter
from aegis_connectors.devices.withings import WithingsAdapter

__all__ = [
    "DeviceConnector",
    "HealthKitAdapter",
    "GoogleFitAdapter",
    "FitbitAdapter",
    "GarminAdapter",
    "WithingsAdapter",
]
