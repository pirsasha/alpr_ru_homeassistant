"""ALPR-RU integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import voluptuous as vol

from homeassistant.components.camera import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .api import AlprRuApi, AlprRuError
from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    CONF_CAMERA_ENTITY,
    CONF_PLATE_TYPE,
    DEFAULT_PLATE_TYPE,
    DOMAIN,
    EVENT_PLATE_DETECTED,
    PLATE_TYPES,
    PLATFORMS,
    SERVICE_RECOGNIZE,
    SIGNAL_RESULT,
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(CONF_PLATE_TYPE, default=DEFAULT_PLATE_TYPE): vol.In(PLATE_TYPES),
    }
)


@dataclass(slots=True)
class AlprRuRuntime:
    """Runtime state shared by ALPR-RU entities."""

    hass: HomeAssistant
    entry: ConfigEntry
    api: AlprRuApi
    default_camera: str
    default_plate_type: str
    last_result: dict[str, Any] = field(default_factory=dict)

    async def async_recognize(
        self,
        camera_entity: str | None = None,
        plate_type: str | None = None,
    ) -> dict[str, Any]:
        """Capture one image from HA and send it to ALPR-RU."""
        target_camera = camera_entity or self.default_camera
        target_plate_type = plate_type or self.default_plate_type

        try:
            image = await async_get_image(self.hass, target_camera, timeout=15)
        except Exception as err:
            raise HomeAssistantError(
                f"Не удалось получить кадр с {target_camera}: {err}"
            ) from err

        try:
            result = await self.api.async_recognize(
                image.content,
                image.content_type,
                target_plate_type,
            )
        except AlprRuError as err:
            raise HomeAssistantError(f"Ошибка ALPR-RU: {err}") from err

        recognized_at = dt_util.utcnow().isoformat()
        result = dict(result)
        result["camera_entity"] = target_camera
        result["recognized_at"] = recognized_at
        self.last_result = result

        async_dispatcher_send(
            self.hass,
            SIGNAL_RESULT.format(entry_id=self.entry.entry_id),
            result,
        )

        plate = str(result.get("plate") or "").strip()
        if result.get("ok") and plate:
            self.hass.bus.async_fire(
                EVENT_PLATE_DETECTED,
                {
                    "camera_entity": target_camera,
                    "plate": plate,
                    "confidence": result.get("confidence"),
                    "valid_format": result.get("valid_format"),
                    "detector_confidence": result.get("detector_confidence"),
                    "bbox": result.get("bbox"),
                    "recognized_at": recognized_at,
                },
            )

        return result


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the ALPR-RU domain and global recognize service."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_recognize(call: ServiceCall) -> None:
        runtimes = list(hass.data.get(DOMAIN, {}).values())
        if not runtimes:
            raise HomeAssistantError("ALPR-RU integration is not configured")

        runtime: AlprRuRuntime = runtimes[0]
        await runtime.async_recognize(
            camera_entity=call.data[CONF_ENTITY_ID],
            plate_type=call.data.get(CONF_PLATE_TYPE),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RECOGNIZE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RECOGNIZE,
            handle_recognize,
            schema=SERVICE_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ALPR-RU from a config entry."""
    session = async_get_clientsession(hass)
    api = AlprRuApi(
        session,
        entry.data[CONF_API_URL],
        entry.data[CONF_API_KEY],
    )

    runtime = AlprRuRuntime(
        hass=hass,
        entry=entry,
        api=api,
        default_camera=entry.data[CONF_CAMERA_ENTITY],
        default_plate_type=entry.data.get(CONF_PLATE_TYPE, DEFAULT_PLATE_TYPE),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an ALPR-RU config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
