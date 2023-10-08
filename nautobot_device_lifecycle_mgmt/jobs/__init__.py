"""Nautobot Jobs for the Device Lifecycle plugin."""
from nautobot.core.celery import register_jobs

from .cve_tracking import GenerateVulnerabilities
from .lifecycle_reporting import DeviceSoftwareValidationFullReport, InventoryItemSoftwareValidationFullReport
from .get_os_version import CreateSoftwareRel

jobs = [
    DeviceSoftwareValidationFullReport,
    InventoryItemSoftwareValidationFullReport,
    GenerateVulnerabilities,
    CreateSoftwareRel,
]
register_jobs(*jobs)
