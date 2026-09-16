"""Sensor platform for Arctic Spa."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ArcticSpaEntity

SENSORS = [
    # (key, name, json_key, unit, device_class, state_class, icon, value_fn, entity_category)
    (
        "temperature",
        "Temperature",
        "temperatureF",
        UnitOfTemperature.FAHRENHEIT,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        None,
        None,
        None,
    ),
    (
        "setpoint",
        "Setpoint",
        "setpointF",
        UnitOfTemperature.FAHRENHEIT,
        SensorDeviceClass.TEMPERATURE,
        None,
        None,
        None,
        None,
    ),
    (
        "ph",
        "pH",
        "ph",
        "pH",
        None,
        SensorStateClass.MEASUREMENT,
        "mdi:test-tube",
        None,
        None,
    ),
    (
        "ph_status",
        "pH Status",
        "ph_status",
        None,
        None,
        None,
        "mdi:test-tube",
        lambda v: v.replace("_", " ").title() if isinstance(v, str) else v,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "orp",
        "ORP",
        "orp",
        "mV",
        None,
        SensorStateClass.MEASUREMENT,
        "mdi:flash",
        None,
        None,
    ),
    (
        "orp_status",
        "ORP Status",
        "orp_status",
        None,
        None,
        None,
        "mdi:flash",
        lambda v: v.replace("_", " ").title() if isinstance(v, str) else v,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "filter_status",
        "Filter Status",
        "filter_status",
        None,
        None,
        None,
        "mdi:air-filter",
        None,
        EntityCategory.DIAGNOSTIC,
    ),
    (
        "filtration_duration",
        "Filtration Duration",
        "filtration_duration",
        UnitOfTime.HOURS,
        None,
        None,
        "mdi:timer-outline",
        None,
        None,
    ),
    (
        "filtration_frequency",
        "Filtration Frequency",
        "filtration_frequency",
        "x/day",
        None,
        None,
        "mdi:refresh",
        None,
        None,
    ),
    (
        "pump1_state",
        "Pump 1 State",
        "pump1",
        None,
        None,
        None,
        "mdi:pump",
        None,
        None,
    ),
    (
        "pump2_state",
        "Pump 2 State",
        "pump2",
        None,
        None,
        None,
        "mdi:pump",
        None,
        None,
    ),
    (
        "pump3_state",
        "Pump 3 State",
        "pump3",
        None,
        None,
        None,
        "mdi:pump",
        None,
        None,
    ),
    (
        "errors",
        "Errors",
        "errors",
        None,
        None,
        None,
        "mdi:alert-circle-outline",
        lambda v: ", ".join(v) if isinstance(v, list) and v else "None",
        EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Arctic Spa sensors."""
    coordinator = entry.runtime_data

    entities = []
    for key, name, json_key, unit, dev_cls, state_cls, icon, value_fn, entity_cat in SENSORS:
        entities.append(
            ArcticSpaSensor(
                coordinator,
                entry.entry_id,
                key,
                name,
                json_key,
                unit,
                dev_cls,
                state_cls,
                icon,
                value_fn,
                entity_cat,
            )
        )
    async_add_entities(entities)


class ArcticSpaSensor(ArcticSpaEntity, SensorEntity):
    """Representation of an Arctic Spa sensor."""

    def __init__(
        self,
        coordinator,
        entry_id,
        key,
        name,
        json_key,
        unit,
        device_class,
        state_class,
        icon,
        value_fn,
        entity_category,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, key, name)
        self._json_key = json_key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._value_fn = value_fn
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get(self._json_key)
        if self._value_fn and val is not None:
            return self._value_fn(val)
        return val
