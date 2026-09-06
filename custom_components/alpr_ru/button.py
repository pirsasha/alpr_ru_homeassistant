"""Recognition button for ALPR-RU."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AlprRuRuntime
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ALPR-RU button."""
    runtime: AlprRuRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AlprRuRecognizeButton(runtime)])


class AlprRuRecognizeButton(ButtonEntity):
    """Capture the configured camera and recognize a plate now."""

    _attr_has_entity_name = True
    _attr_name = "Распознать сейчас"
    _attr_icon = "mdi:camera-iris"

    def __init__(self, runtime: AlprRuRuntime) -> None:
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_recognize"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name="ALPR-RU",
            manufacturer="PirogovX",
            model="Cloud ALPR",
        )

    async def async_press(self) -> None:
        """Recognize one frame from the configured default camera."""
        await self._runtime.async_recognize()
