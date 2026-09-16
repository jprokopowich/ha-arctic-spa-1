"""Binary sensor platform for Arctic Spa."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArcticSpaEntity

BINARY_SENSORS = [
    # (key, name, device_class, icon, value_fn, entity_category)
    (
        "connected",
        "Connected",
        BinarySensorDeviceClass.CONNECTIVITY,
        None,
        lambda d: d.get("connected", False),
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "spaboy_connected",
        "SpaBoy Connected",
        BinarySensorDeviceClass.CONNECTIVITY,
        None,
        lambda d: d.get("spaboy_connected", False),
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "spaboy_producing",
        "SpaBoy Producing",
        None,
        "mdi:flask",
        lambda d: d.get("spaboy_producing", False),
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "lights",
        "Lights",
        BinarySensorDeviceClass.LIGHT,
        None,
        lambda d: d.get("lights") == "on",
        None,
    ),
    (
        "filter_suspension",
        "Filter Suspension",
        None,
        "mdi:air-filter",
        lambda d: d.get("filter_suspension") == "on",
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "pump1_running",
        "Pump 1 Running",
        BinarySensorDeviceClass.RUNNING,
        None,
        lambda d: d.get("pump1", "off") != "off",
        None,
    ),
    (
        "pump2_running",
        "Pump 2 Running",
        BinarySensorDeviceClass.RUNNING,
        None,
        lambda d: d.get("pump2", "off") != "off",
        None,
    ),
    (
        "pump3_running",
        "Pump 3 Running",
        BinarySensorDeviceClass.RUNNING,
        None,
        lambda d: d.get("pump2", "off") != "off",
        None,
    ),
    (
        "has_errors",
        "Has Errors",
        BinarySensorDeviceClass.PROBLEM,
        None,
        lambda d: len(d.get("errors", [])) > 0,
        EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Arctic Spa binary sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        ArcticSpaBinarySensor(
            coordinator, entry.entry_id, key, name, dev_cls, icon, value_fn, entity_cat
        )
        for key, name, dev_cls, icon, value_fn, entity_cat in BINARY_SENSORS
    )


class ArcticSpaBinarySensor(ArcticSpaEntity, BinarySensorEntity):
    """Representation of an Arctic Spa binary sensor."""

    def __init__(  # noqa: PLR0913
        self, coordinator, entry_id, key, name, device_class, icon, value_fn, entity_category
    ):
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id, key, name)
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._value_fn = value_fn
        self._attr_entity_category = entity_category

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return self._value_fn(self.coordinator.data)
