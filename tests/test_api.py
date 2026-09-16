"""Tests for the Arctic Spa API client."""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

# Stub out homeassistant modules so we can import api.py without HA installed
ha_mock = ModuleType("homeassistant")
ha_mock.config_entries = MagicMock()
ha_mock.const = MagicMock()
ha_mock.const.CONF_API_KEY = "api_key"
ha_mock.core = MagicMock()
ha_mock.helpers = MagicMock()
ha_mock.helpers.update_coordinator = MagicMock()
ha_mock.helpers.entity = MagicMock()
ha_mock.helpers.device_registry = MagicMock()
ha_mock.helpers.aiohttp_client = MagicMock()
ha_mock.helpers.entity_platform = MagicMock()
ha_mock.components = MagicMock()
for mod in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.switch",
    "homeassistant.components.number",
]:
    sys.modules.setdefault(mod, MagicMock())

import aiohttp  # noqa: E402
import pytest  # noqa: E402

from custom_components.arctic_spa.api import (  # noqa: E402
    ArcticSpaApiError,
    ArcticSpaAuthError,
    ArcticSpaClient,
    ArcticSpaConnectionError,
    LightState,
    PumpState,
    SpaStatus,
)

MOCK_STATUS_RESPONSE = {
    "connected": True,
    "temperatureF": 100,
    "setpointF": 100,
    "lights": "off",
    "spaboy_connected": True,
    "spaboy_producing": False,
    "ph": 7.46,
    "ph_status": "OK",
    "orp": 553,
    "orp_status": "OK",
    "pump1": "off",
    "pump2": "off",
    "filter_status": "Idle",
    "filtration_duration": 1,
    "filtration_frequency": 1,
    "filter_suspension": "on",
    "errors": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status: int = 200, json_data: dict | None = None) -> AsyncMock:
    """Return a mock aiohttp response."""
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(
        return_value=json_data if json_data is not None else MOCK_STATUS_RESPONSE
    )
    return response


def _make_session(response: AsyncMock) -> MagicMock:
    """Return a mock aiohttp ClientSession wired to the given response."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.closed = False

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)

    session.get = MagicMock(return_value=cm)
    session.put = MagicMock(return_value=cm)
    return session


# ---------------------------------------------------------------------------
# SpaStatus
# ---------------------------------------------------------------------------


class TestSpaStatus:
    """Tests for SpaStatus dataclass."""

    def test_from_dict_full(self):
        """All fields present in API response."""
        status = SpaStatus.from_dict(MOCK_STATUS_RESPONSE)
        assert status.connected is True
        assert status.temperature_f == 100
        assert status.setpoint_f == 100
        assert status.lights == "off"
        assert status.pump1 == "off"
        assert status.pump2 == "off"
        assert status.ph == 7.46
        assert status.ph_status == "OK"
        assert status.orp == 553
        assert status.filter_status == "Idle"
        assert status.filtration_duration == 1
        assert status.filtration_frequency == 1
        assert status.errors == []

    def test_from_dict_empty(self):
        """Defaults apply when no keys present."""
        status = SpaStatus.from_dict({})
        assert status.connected is False
        assert status.temperature_f == 0
        assert status.setpoint_f == 0
        assert status.lights == "off"
        assert status.pump1 == "off"
        assert status.pump2 == "off"
        assert status.ph == 0.0
        assert status.ph_status == "UNKNOWN"
        assert status.orp == 0
        assert status.orp_status == "UNKNOWN"
        assert status.filter_status == "Unknown"
        assert status.filtration_duration == 1
        assert status.filtration_frequency == 1
        assert status.filter_suspension == "off"
        assert status.errors == []

    def test_from_dict_partial(self):
        """Some keys present, rest fall back to defaults."""
        status = SpaStatus.from_dict({"connected": True, "temperatureF": 104, "errors": ["E01"]})
        assert status.connected is True
        assert status.temperature_f == 104
        assert status.lights == "off"  # default
        assert status.errors == ["E01"]
        assert status.ph == 0.0  # default

    def test_from_dict_extreme_temperatures(self):
        """Edge case: very high and very low temperature values."""
        status_hot = SpaStatus.from_dict({"temperatureF": 212, "setpointF": 212})
        assert status_hot.temperature_f == 212

        status_cold = SpaStatus.from_dict({"temperatureF": 32, "setpointF": 32})
        assert status_cold.temperature_f == 32

    def test_from_dict_multiple_errors(self):
        """Multiple errors in list."""
        status = SpaStatus.from_dict({"errors": ["E01", "E02", "E03"]})
        assert status.errors == ["E01", "E02", "E03"]

    def test_from_dict_pumps_running(self):
        """Pump states other than 'off'."""
        status = SpaStatus.from_dict({"pump1": "low", "pump2": "high"})
        assert status.pump1 == "low"
        assert status.pump2 == "high"


# ---------------------------------------------------------------------------
# GET request paths
# ---------------------------------------------------------------------------


class TestGetRequests:
    """Tests for _get and methods that use it."""

    @pytest.mark.asyncio
    async def test_get_status_success(self):
        """Happy-path GET returns parsed SpaStatus."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        status = await client.async_get_status()
        assert status.connected is True
        assert status.temperature_f == 100
        assert status.ph == 7.46

    @pytest.mark.asyncio
    async def test_get_status_raw_success(self):
        """async_get_status_raw returns the raw dict."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        data = await client.async_get_status_raw()
        assert data == MOCK_STATUS_RESPONSE

    @pytest.mark.asyncio
    async def test_get_401_raises_auth_error(self):
        """HTTP 401 on GET raises ArcticSpaAuthError."""
        client = ArcticSpaClient("bad_key", session=_make_session(_make_response(status=401)))
        with pytest.raises(ArcticSpaAuthError):
            await client.async_get_status()

    @pytest.mark.asyncio
    async def test_get_500_raises_api_error(self):
        """HTTP 500 on GET raises ArcticSpaApiError."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response(status=500)))
        with pytest.raises(ArcticSpaApiError):
            await client.async_get_status()

    @pytest.mark.asyncio
    async def test_get_403_raises_api_error(self):
        """HTTP 403 on GET raises ArcticSpaApiError."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response(status=403)))
        with pytest.raises(ArcticSpaApiError):
            await client.async_get_status()

    @pytest.mark.asyncio
    async def test_get_429_raises_api_error(self):
        """HTTP 429 (rate-limit) on GET raises ArcticSpaApiError."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response(status=429)))
        with pytest.raises(ArcticSpaApiError):
            await client.async_get_status()

    @pytest.mark.asyncio
    async def test_get_connection_error_raises_connection_error(self):
        """aiohttp.ClientError on GET is wrapped in ArcticSpaConnectionError."""
        session = MagicMock(spec=aiohttp.ClientSession)
        session.closed = False
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("network failure"))
        cm.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=cm)

        client = ArcticSpaClient("test_key", session=session)
        with pytest.raises(ArcticSpaConnectionError, match="Connection error"):
            await client.async_get_status()

    @pytest.mark.asyncio
    async def test_get_connection_error_is_subclass_of_api_error(self):
        """ArcticSpaConnectionError is a subclass of ArcticSpaApiError."""
        session = MagicMock(spec=aiohttp.ClientSession)
        session.closed = False
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("timeout"))
        cm.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=cm)

        client = ArcticSpaClient("test_key", session=session)
        with pytest.raises(ArcticSpaApiError):  # broad catch still works
            await client.async_get_status()


# ---------------------------------------------------------------------------
# PUT request paths
# ---------------------------------------------------------------------------


class TestPutRequests:
    """Tests for _put and all command methods."""

    @pytest.mark.asyncio
    async def test_set_lights_on(self):
        """async_set_lights with ON returns None (no exception)."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_lights(LightState.ON)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_lights_off(self):
        """async_set_lights with OFF returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_lights(LightState.OFF)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_pump_high(self):
        """async_set_pump with HIGH returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_pump(1, PumpState.HIGH)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_pump_low(self):
        """async_set_pump with LOW returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_pump(2, PumpState.LOW)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_pump_off(self):
        """async_set_pump with OFF returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_pump(1, PumpState.OFF)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_pump_3(self):
        """async_set_pump with pump_id 3 returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_pump(3, PumpState.HIGH)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_pump_invalid_id_raises_value_error(self):
        """pump_id outside {1, 2, 3} raises ValueError immediately (no network call)."""
        session = _make_session(_make_response())
        client = ArcticSpaClient("test_key", session=session)
        with pytest.raises(ValueError, match="Invalid pump_id"):
            await client.async_set_pump(0, PumpState.HIGH)
        with pytest.raises(ValueError, match="Invalid pump_id"):
            await client.async_set_pump(4, PumpState.LOW)
        # Confirm no PUT was issued
        session.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_temperature(self):
        """async_set_temperature returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_temperature(102)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_filtration(self):
        """async_set_filtration returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_filtration(2, 3)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_boost_on(self):
        """async_set_boost(True) returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_boost(True)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_boost_off(self):
        """async_set_boost(False) returns None."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response()))
        result = await client.async_set_boost(False)
        assert result is None

    @pytest.mark.asyncio
    async def test_put_401_raises_auth_error(self):
        """HTTP 401 on PUT raises ArcticSpaAuthError."""
        client = ArcticSpaClient("bad_key", session=_make_session(_make_response(status=401)))
        with pytest.raises(ArcticSpaAuthError):
            await client.async_set_lights(LightState.ON)

    @pytest.mark.asyncio
    async def test_put_500_raises_api_error(self):
        """HTTP 500 on PUT raises ArcticSpaApiError."""
        client = ArcticSpaClient("test_key", session=_make_session(_make_response(status=500)))
        with pytest.raises(ArcticSpaApiError):
            await client.async_set_lights(LightState.ON)

    @pytest.mark.asyncio
    async def test_put_connection_error_raises_connection_error(self):
        """aiohttp.ClientError on PUT is wrapped in ArcticSpaConnectionError."""
        session = MagicMock(spec=aiohttp.ClientSession)
        session.closed = False
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("connection refused"))
        cm.__aexit__ = AsyncMock(return_value=False)
        session.put = MagicMock(return_value=cm)

        client = ArcticSpaClient("test_key", session=session)
        with pytest.raises(ArcticSpaConnectionError, match="Connection error"):
            await client.async_set_lights(LightState.ON)

    @pytest.mark.asyncio
    async def test_put_sends_correct_payload_lights(self):
        """async_set_lights sends {"state": "on"} to the lights endpoint."""
        session = _make_session(_make_response())
        client = ArcticSpaClient("test_key", session=session)
        await client.async_set_lights(LightState.ON)
        call_kwargs = session.put.call_args
        assert "lights" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"] == {"state": "on"}

    @pytest.mark.asyncio
    async def test_put_sends_correct_payload_boost_off(self):
        """async_set_boost(False) sends {"state": "off"} to the boost endpoint."""
        session = _make_session(_make_response())
        client = ArcticSpaClient("test_key", session=session)
        await client.async_set_boost(False)
        call_kwargs = session.put.call_args
        assert "boost" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"] == {"state": "off"}

    @pytest.mark.asyncio
    async def test_put_sends_correct_payload_pump(self):
        """async_set_pump sends correct endpoint and payload."""
        session = _make_session(_make_response())
        client = ArcticSpaClient("test_key", session=session)
        await client.async_set_pump(2, PumpState.HIGH)
        call_kwargs = session.put.call_args
        assert "pumps/2" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"] == {"state": "high"}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    """Tests for session creation and teardown."""

    @pytest.mark.asyncio
    async def test_external_session_not_closed_on_close(self):
        """When an external session is injected, close() must not close it."""
        external_session = _make_session(_make_response())
        external_session.close = AsyncMock()
        client = ArcticSpaClient("test_key", session=external_session)
        await client.close()
        external_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_owned_session_closed_on_close(self):
        """When the client creates its own session, close() shuts it down."""
        mock_session = _make_session(_make_response())
        mock_session.close = AsyncMock()

        with patch(
            "custom_components.arctic_spa.api.aiohttp.ClientSession", return_value=mock_session
        ):
            client = ArcticSpaClient("test_key")  # no session → will create one
            await client._get_session()  # trigger session creation
            await client.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_recreates_closed_session(self):
        """_get_session() creates a fresh session when the current one is closed."""
        original_session = _make_session(_make_response())
        original_session.closed = True  # simulate a closed session

        new_session = _make_session(_make_response())

        with patch(
            "custom_components.arctic_spa.api.aiohttp.ClientSession", return_value=new_session
        ):
            client = ArcticSpaClient("test_key", session=original_session)
            session = await client._get_session()

        assert session is new_session

    @pytest.mark.asyncio
    async def test_close_noop_when_no_session(self):
        """close() with no session ever created does not raise."""
        client = ArcticSpaClient("test_key")
        await client.close()  # should not raise
