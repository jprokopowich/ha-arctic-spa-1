"""Switch platform for Arctic Spa."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ArcticSpaApiError, LightState, PumpState
from .entity import ArcticSpaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Arctic Spa switches."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            ArcticSpaLightSwitch(coordinator, entry.entry_id),
            ArcticSpaPumpSwitch(coordinator, entry.entry_id, 1, "Pump 1 Jets", PumpState.HIGH),
            ArcticSpaPumpSwitch(coordinator, entry.entry_id, 2, "Pump 2 Jets", PumpState.HIGH),
            ArcticSpaPumpSwitch(coordinator, entry.entry_id, 3, "Pump 3 Jets", PumpState.HIGH),
            ArcticSpaBoostSwitch(coordinator, entry.entry_id),
        ]
    )


class ArcticSpaLightSwitch(ArcticSpaEntity, SwitchEntity):
    """Switch for spa lights."""

    def __init__(self, coordinator, entry_id):
        """Initialize the light switch."""
        super().__init__(coordinator, entry_id, "lights_switch", "Lights")

    @property
    def is_on(self) -> bool | None:
        """Return true if lights are on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("lights") == "on"

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        return "mdi:lightbulb-on" if self.is_on else "mdi:lightbulb-off-outline"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the lights."""
        try:
            await self.coordinator.client.async_set_lights(LightState.ON)
            await self.coordinator.async_request_refresh()
        except ArcticSpaApiError as err:
            _LOGGER.error("Failed to turn on lights: %s", err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the lights."""
        try:
            await self.coordinator.client.async_set_lights(LightState.OFF)
            await self.coordinator.async_request_refresh()
        except ArcticSpaApiError as err:
            _LOGGER.error("Failed to turn off lights: %s", err)


class ArcticSpaPumpSwitch(ArcticSpaEntity, SwitchEntity):
    """Switch for spa pumps."""

    def __init__(self, coordinator, entry_id, pump_id, name, on_state):
        """Initialize the pump switch."""
        super().__init__(coordinator, entry_id, f"pump{pump_id}_switch", name)
        self._pump_id = pump_id
        self._on_state = on_state

    @property
    def is_on(self) -> bool | None:
        """Return true if pump is running."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(f"pump{self._pump_id}", "off") != "off"

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the pump."""
        try:
            await self.coordinator.client.async_set_pump(self._pump_id, self._on_state)
            await self.coordinator.async_request_refresh()
        except ArcticSpaApiError as err:
            _LOGGER.error("Failed to turn on pump %s: %s", self._pump_id, err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the pump."""
        try:
            await self.coordinator.client.async_set_pump(self._pump_id, PumpState.OFF)
            await self.coordinator.async_request_refresh()
        except ArcticSpaApiError as err:
            _LOGGER.error("Failed to turn off pump %s: %s", self._pump_id, err)


class ArcticSpaBoostSwitch(ArcticSpaEntity, SwitchEntity):
    """Switch for boost mode."""

    _attr_icon = "mdi:rocket-launch"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry_id):
        """Initialize the boost switch."""
        super().__init__(coordinator, entry_id, "boost_switch", "Boost Mode")
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return true if boost is on."""
        # Boost state isn't exposed in the status API, track locally
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on boost mode."""
        try:
            await self.coordinator.client.async_set_boost(True)
            self._is_on = True
            self.async_write_ha_state()
        except ArcticSpaApiError as err:
            _LOGGER.error("Failed to enable boost mode: %s", err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off boost mode."""
        try:
            await self.coordinator.client.async_set_boost(False)
            self._is_on = False
            self.async_write_ha_state()
        except ArcticSpaApiError as err:
            _LOGGER.error("Failed to disable boost mode: %s", err)
