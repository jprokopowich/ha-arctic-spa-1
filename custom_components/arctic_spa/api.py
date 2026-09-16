"""Arctic Spa API client library."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://api.myarcticspa.com/v2/spa"


class PumpState(StrEnum):
    """Pump states."""

    OFF = "off"
    LOW = "low"
    HIGH = "high"


class LightState(StrEnum):
    """Light states."""

    OFF = "off"
    ON = "on"


@dataclass
class SpaStatus:
    """Parsed spa status."""

    connected: bool
    temperature_f: int
    setpoint_f: int
    lights: str
    pump1: str
    pump2: str
    pump3: str
    spaboy_connected: bool
    spaboy_producing: bool
    ph: float
    ph_status: str
    orp: int
    orp_status: str
    filter_status: str
    filtration_duration: int
    filtration_frequency: int
    filter_suspension: str
    errors: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> SpaStatus:
        """Create SpaStatus from API response dict."""
        return cls(
            connected=data.get("connected", False),
            temperature_f=data.get("temperatureF", 0),
            setpoint_f=data.get("setpointF", 0),
            lights=data.get("lights", "off"),
            pump1=data.get("pump1", "off"),
            pump2=data.get("pump2", "off"),
            pump3=data.get("pump3", "off"),
            spaboy_connected=data.get("spaboy_connected", False),
            spaboy_producing=data.get("spaboy_producing", False),
            ph=data.get("ph", 0.0),
            ph_status=data.get("ph_status", "UNKNOWN"),
            orp=data.get("orp", 0),
            orp_status=data.get("orp_status", "UNKNOWN"),
            filter_status=data.get("filter_status", "Unknown"),
            filtration_duration=data.get("filtration_duration", 1),
            filtration_frequency=data.get("filtration_frequency", 1),
            filter_suspension=data.get("filter_suspension", "off"),
            errors=data.get("errors", []),
        )


class ArcticSpaApiError(Exception):
    """Base exception for Arctic Spa API errors."""


class ArcticSpaAuthError(ArcticSpaApiError):
    """Authentication error."""


class ArcticSpaConnectionError(ArcticSpaApiError):
    """Connection error."""


class ArcticSpaClient:
    """Client for the Arctic Spa cloud API.

    API documentation: https://api.myarcticspa.com/docs
    """

    def __init__(self, api_key: str, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the client.

        Args:
            api_key: Arctic Spa API key from myarcticspa.com
            session: Optional aiohttp session (one will be created if not provided)
        """
        self._api_key = api_key
        self._session = session
        self._own_session = session is None

    @property
    def _headers(self) -> dict[str, str]:
        """Return request headers."""
        return {
            "X-API-KEY": self._api_key,
            "Content-Type": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, endpoint: str) -> dict:
        """Send a GET request."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{API_BASE_URL}/{endpoint}",
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise ArcticSpaAuthError("Invalid API key")
                if resp.status != 200:
                    raise ArcticSpaApiError(f"API returned status {resp.status}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise ArcticSpaConnectionError(f"Connection error: {err}") from err

    async def _put(self, endpoint: str, payload: dict) -> None:
        """Send a PUT request, raising on any error."""
        session = await self._get_session()
        try:
            async with session.put(
                f"{API_BASE_URL}/{endpoint}",
                headers=self._headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    raise ArcticSpaAuthError("Invalid API key")
                if resp.status != 200:
                    raise ArcticSpaApiError(f"PUT {endpoint} returned status {resp.status}")
        except aiohttp.ClientError as err:
            raise ArcticSpaConnectionError(f"Connection error on PUT {endpoint}: {err}") from err

    async def async_get_status(self) -> SpaStatus:
        """Get current spa status."""
        data = await self._get("status")
        return SpaStatus.from_dict(data)

    async def async_get_status_raw(self) -> dict:
        """Get current spa status as raw dict (for coordinator)."""
        return await self._get("status")

    # ── Lights ──

    async def async_set_lights(self, state: LightState | str) -> None:
        """Turn lights on or off."""
        await self._put("lights", {"state": str(state)})

    # ── Pumps ──

    async def async_set_pump(self, pump_id: int, state: PumpState | str) -> None:
        """Set pump state (off, low, high)."""
        if pump_id not in (1, 2, 3):
            raise ValueError(f"Invalid pump_id {pump_id!r}: must be 1 or 2 or 3")
        await self._put(f"pumps/{pump_id}", {"state": str(state)})

    # ── Temperature ──

    async def async_set_temperature(self, setpoint_f: int) -> None:
        """Set the target temperature in Fahrenheit."""
        await self._put("temperature", {"setpointF": setpoint_f})

    # ── Filtration ──

    async def async_set_filtration(self, duration: int, frequency: int) -> None:
        """Set filtration schedule."""
        await self._put("filter", {"duration": duration, "frequency": frequency})

    # ── Boost ──

    async def async_set_boost(self, on: bool) -> None:
        """Turn boost mode on or off."""
        await self._put("boost", {"state": "on" if on else "off"})
