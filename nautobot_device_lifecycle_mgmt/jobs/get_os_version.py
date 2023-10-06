from django.contrib.contenttypes.models import ContentType

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.extras.jobs import Job, ObjectVar, MultiObjectVar, BooleanVar, TextVar
from nautobot.extras.models import Tag, Relationship, RelationshipAssociation
from nautobot.extras.models.statuses import Status
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Manufacturer,
    Platform,
    Rack,
    RackGroup,
)
from nautobot.extras.models.roles import Role
from nautobot.dcim.models.locations import Location, LocationType
from nautobot.dcim.filters import DeviceFilterSet

from nautobot_device_lifecycle_mgmt.models import SoftwareLCM
from nautobot_device_lifecycle_mgmt.models import SoftwareImageLCM

from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory

from nornir_nautobot.exceptions import NornirNautobotException

from nornir import InitNornir
from nornir.core.inventory import Host
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from nornir_napalm.plugins.tasks import napalm_get

# Need to replicate this functionality
# from nautobot_golden_config.utilities.helper import get_job_filter

name = "Testing"

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)

FIELDS_PK = {
    "platform",
    "tenant_group",
    "tenant",
    "location",
    "role",
    "rack",
    "rack_group",
    "manufacturer",
    "device_type",
    #"device",
}

FIELDS_NAME = {"tags", "status"}


def get_job_filter(data=None):
    """Helper function to return a list of devices based on form inputs."""
    if not data:
        data = {}
    query = {}

    # Translate instances from FIELDS set to list of primary keys
    for field in FIELDS_PK:
        if data.get(field):
            query[field] = data[field].values_list("pk", flat=True)

    # Translate instances from FIELDS set to list of names
    for field in FIELDS_NAME:
        if data.get(field):
            query[field] = data[field].values_list("name", flat=True)

    # Not sure about this, maybe need to handle devices differently?
    # Handle case where object is from single device run all.
    if data.get("device") and isinstance(data["device"], Device):
        query.update({"id": [str(data["device"].pk)]})
    elif data.get("device"):
        query.update({"id": data["device"].values_list("pk", flat=True)})

    devices_filtered = DeviceFilterSet(data=query)

    devices_no_platform = devices_filtered.qs.filter(platform__isnull=True)
    if devices_no_platform.exists():
        raise NornirNautobotException(
            f"`E3017:` The following device(s) {', '.join([device.name for device in devices_no_platform])} have no platform defined. Platform is required."
        )

    devices_no_primary_ip = devices_filtered.qs.filter(primary_ip4__isnull=True)
    if devices_no_primary_ip.exists():
        raise NornirNautobotException(
            f"The following device(s) {', '.join([device.name for device in devices_no_primary_ip])} have no primary IP address defined. A primary IP is required."
        )

    return devices_filtered.qs


def init_nornir(data) -> InitNornir:
    """Initialise Nornir object."""
        
    #device_qs = Device.objects.all()
    return InitNornir(
        runner=NORNIR_SETTINGS.get("runner"),
        logging={"enabled": False},
        # dry_run=data["dry_run"],
        inventory={
            "plugin": "nautobot-inventory",
            "options": {
                "credentials_class": NORNIR_SETTINGS.get("credentials"),
                "params": NORNIR_SETTINGS.get("inventory_params"),
                "queryset": get_job_filter(data),
                #"queryset": Device.objects.all()
            },
        },
    )


class FormEntry:  # pylint disable=too-few-public-method
    """Class definition to use as Mixin for form definitions."""

    tenant_group = MultiObjectVar(model=TenantGroup, required=False)
    tenant = MultiObjectVar(model=Tenant, required=False)
    location = MultiObjectVar(model=Location, required=False)
    rack_group = MultiObjectVar(model=RackGroup, required=False)
    rack = MultiObjectVar(model=Rack, required=False)
    role = MultiObjectVar(model=Role, required=False)
    manufacturer = MultiObjectVar(model=Manufacturer, required=False)
    platform = MultiObjectVar(model=Platform, required=False)
    device_type = MultiObjectVar(model=DeviceType, required=False, display_field="display_name")
    device = MultiObjectVar(model=Device, required=False)
    tags = MultiObjectVar(
        model=Tag, required=False, display_field="name", query_params={"content_types": "dcim.device"}
    )
    status = MultiObjectVar(
        model=Status,
        required=False,
        query_params={"content_types": Device._meta.label_lower},
        display_field="label",
        label="Device Status",
    )
    debug = BooleanVar(description="Enable for more verbose debug logging")


class CreateSoftwareRel(Job, FormEntry):
    """Retrieve os_version from running device and update device to software relationship."""

    class Meta:
        """Job attributes."""

        name = "Get Device OS Version"
        description = "Get OS version, build device to software relationship"
        read_only = False
        has_sensitive_variables = False

    def run(self, *args, **data) -> None:
        """Run get os version job."""
        # Init Nornir and run build_software_rel task for each device
        try:
            with init_nornir(data) as nornir_obj:
                nr = nornir_obj
                nr.run(
                    #task=self.get_os_version,
                    task=self.create_software_to_device_rel,
                    name=self.name,
                )
        except Exception as err:
            self.logger.debug(f"```\n{err}\n```")
            raise

    def get_os_version(self, task: Task, device_obj) -> str:
        """Get os_version from device via nornir-napalm."""
        try:
            return task.run(task=napalm_get, getters="get_facts").result["get_facts"]["os_version"]
        except Exception as err:
            self.logger.error(f"{err}")

    def get_or_create_software_obj(self, os_version, device_obj):
        """Get or create SoftwareLCM object for device."""
        software_obj = SoftwareLCM.objects.get_or_create(version=os_version, device_platform=device_obj.platform)
        if not software_obj[1]:
            self.logger.info(f"Created software {software_obj[0].version} for {software_obj[0].device_platform}.")
        return software_obj[0]
            
    def create_rel(self, software_obj, device_obj):
        """Create relationship between device and software objects."""
        software_rel_obj = Relationship.objects.get(key="device_soft")

        # Does it already have a relationship to the correct software
        intended_rel = RelationshipAssociation.objects.filter(relationship=software_rel_obj, destination_id=device_obj.id, source_id=software_obj.id)
        if not intended_rel.exists():
            # Does it have a relationship to some other (non-correct) software
            actual_rel = RelationshipAssociation.objects.filter(relationship=software_rel_obj, destination_id=device_obj.id)
            if actual_rel.exists():
                actual_rel.delete()
            # Create intended relationship
            source_ct = ContentType.objects.get(model="softwarelcm")
            dest_ct = ContentType.objects.get(model="device")
            created_rel = RelationshipAssociation.objects.create(
                relationship=software_rel_obj,
                source_type=source_ct,
                source=software_obj,
                destination_type=dest_ct,
                destination=device_obj,
            )
            self.logger.info(f"Created relationship: {created_rel}.")
            return

        self.logger.info(f"Correct relationship exists: {intended_rel}.")


    def create_software_to_device_rel(self, task):
        """Create relationship between Device and Software objects in LCM."""
        device_obj = task.host.data["obj"]

        os_version = self.get_os_version(task, device_obj)
        software_obj = self.get_or_create_software_obj(os_version, device_obj)
        self.create_rel(software_obj, device_obj)