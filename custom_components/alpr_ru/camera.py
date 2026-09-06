"""Image entities for ALPR-RU."""

from __future__ import annotations

from typing import Any

from homeassistant.components.camera import Camera
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
    """Set up ALPR-RU image cameras."""
    runtime: AlprRuRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AlprRuLastSubmittedCamera(runtime),
            AlprRuLastResultCamera(runtime),
        ]
    )


class AlprRuImageCamera(Camera):
    """Base camera for ALPR-RU retained images."""

    _attr_has_entity_name = True

    def __init__(self, runtime: AlprRuRuntime, suffix: str) -> None:
        super().__init__()
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name="ALPR-RU",
            manufacturer="PirogovX",
            model="Cloud ALPR",
        )
        self._unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to new recognition results."""
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
        """Refresh entity state after recognition."""
        self.async_write_ha_state()


class AlprRuLastSubmittedCamera(AlprRuImageCamera):
    """Exact last frame Home Assistant submitted to ALPR-RU."""

    _attr_name = "Последний отправленный кадр"
    _attr_icon = "mdi:image-arrow-right"

    def __init__(self, runtime: AlprRuRuntime) -> None:
        super().__init__(runtime, "last_submitted_image")

    @property
    def available(self) -> bool:
        """Return whether a frame has been submitted in this HA session."""
        return self._runtime.last_submitted_image is not None

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return the exact JPEG/image bytes sent to ALPR-RU."""
        return self._runtime.last_submitted_image

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose source metadata."""
        return {
            "source_camera": self._runtime.last_result.get("camera_entity"),
            "recognized_at": self._runtime.last_result.get("recognized_at"),
            "content_type": self._runtime.last_submitted_content_type,
        }


class AlprRuLastResultCamera(AlprRuImageCamera):
    """Last plate crop returned by ALPR-RU debug output."""

    _attr_name = "Последний результат ALPR"
    _attr_icon = "mdi:card-account-details-outline"

    def __init__(self, runtime: AlprRuRuntime) -> None:
        super().__init__(runtime, "last_result_image")

    @property
    def available(self) -> bool:
        """Return whether ALPR supplied a result crop URL."""
        return self._runtime.last_result_image_url is not None

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return the last ALPR crop, downloading it once and then caching it."""
        return await self._runtime.async_get_result_image()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose recognition metadata for the displayed crop."""
        result = self._runtime.last_result
        return {
            "plate": result.get("plate"),
            "confidence": result.get("confidence"),
            "detector_confidence": result.get("detector_confidence"),
            "bbox": result.get("bbox"),
            "rectified": result.get("rectified"),
            "recognized_at": result.get("recognized_at"),
            "source_camera": result.get("camera_entity"),
        }
