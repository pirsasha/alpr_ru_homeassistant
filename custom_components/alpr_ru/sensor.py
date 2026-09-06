"""Sensors for ALPR-RU."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AlprRuRuntime
from .const import DOMAIN, SIGNAL_RESULT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the last-plate sensor."""
    runtime: AlprRuRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AlprRuLastPlateSensor(runtime)])


class AlprRuLastPlateSensor(SensorEntity):
    """Last recognized plate from ALPR-RU."""

    _attr_has_entity_name = True
    _attr_name = "Последний номер"
    _attr_icon = "mdi:license"

    def __init__(self, runtime: AlprRuRuntime) -> None:
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_last_plate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name="ALPR-RU",
            manufacturer="PirogovX",
            model="Cloud ALPR",
        )
        self._unsub_dispatcher = None

    @property
    def native_value(self) -> str | None:
        """Return last recognized plate."""
        plate = self._runtime.last_result.get("plate")
        return str(plate) if plate else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful recognition metadata."""
        result = self._runtime.last_result
        return {
            "camera_entity": result.get("camera_entity") or self._runtime.default_camera,
            "trigger_entity": self._runtime.trigger_entity,
            "confidence": result.get("confidence"),
            "valid_format": result.get("valid_format"),
            "detector_confidence": result.get("detector_confidence"),
            "bbox": result.get("bbox"),
            "rectified": result.get("rectified"),
            "recognized_at": result.get("recognized_at"),
            "error": result.get("error"),
            "mode": result.get("mode"),
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to recognition results."""
        await super().async_added_to_hass()
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            SIGNAL_RESULT.format(entry_id=self._runtime.entry.entry_id),
            self._handle_result,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from recognition results."""
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_result(self, _result: dict[str, Any]) -> None:
        self.async_write_ha_state()
