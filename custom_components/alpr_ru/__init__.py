"""ALPR-RU integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.camera import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .api import AlprRuApi, AlprRuError
from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    CONF_CAMERA_ENTITY,
    CONF_PLATE_TYPE,
    CONF_TRIGGER_ENTITY,
    DEFAULT_PLATE_TYPE,
    DOMAIN,
    EVENT_PLATE_DETECTED,
    PLATE_TYPES,
    PLATFORMS,
    SERVICE_RECOGNIZE,
    SIGNAL_RESULT,
)

_LOGGER = logging.getLogger(__name__)

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
    trigger_entity: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)
    trigger_running: bool = False
    last_submitted_image: bytes | None = None
    last_submitted_content_type: str | None = None
    last_result_image_url: str | None = None
    last_result_image: bytes | None = None
    last_result_content_type: str | None = None

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

        # Keep exactly the bytes that are sent to ALPR-RU. This is in-memory
        # only; no snapshot file is written to /config.
        self.last_submitted_image = image.content
        self.last_submitted_content_type = image.content_type

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
        result["trigger_entity"] = self.trigger_entity
        result["recognized_at"] = recognized_at
        self.last_result = result

        # The public API can return relative debug URLs. Prefer the rectified
        # plate crop because it is the closest representation of what OCR saw.
        debug = result.get("debug")
        result_image_url: str | None = None
        if isinstance(debug, dict):
            result_image_url = (
                debug.get("rectified_crop_url")
                or debug.get("crop_url")
                or debug.get("top_crop_url")
                or debug.get("bottom_crop_url")
            )

        self.last_result_image_url = (
            str(result_image_url) if result_image_url else None
        )
        # Invalidate the lazy cache for the new recognition result.
        self.last_result_image = None
        self.last_result_content_type = None

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
                    "trigger_entity": self.trigger_entity,
                    "plate": plate,
                    "confidence": result.get("confidence"),
                    "valid_format": result.get("valid_format"),
                    "detector_confidence": result.get("detector_confidence"),
                    "bbox": result.get("bbox"),
                    "recognized_at": recognized_at,
                },
            )

        return result

    async def async_get_result_image(self) -> bytes | None:
        """Return the cached ALPR result crop, fetching it once if required."""
        if self.last_result_image is not None:
            return self.last_result_image
        if not self.last_result_image_url:
            return None

        try:
            data, content_type = await self.api.async_get_debug_image(
                self.last_result_image_url
            )
        except AlprRuError as err:
            _LOGGER.warning("Unable to load ALPR result image: %s", err)
            return None

        self.last_result_image = data
        self.last_result_content_type = content_type
        return data


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


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload ALPR-RU when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ALPR-RU from a config entry."""
    session = async_get_clientsession(hass)
    api = AlprRuApi(
        session,
        entry.data[CONF_API_URL],
        entry.data[CONF_API_KEY],
    )

    default_camera = entry.options.get(
        CONF_CAMERA_ENTITY,
        entry.data[CONF_CAMERA_ENTITY],
    )
    default_plate_type = entry.options.get(
        CONF_PLATE_TYPE,
        entry.data.get(CONF_PLATE_TYPE, DEFAULT_PLATE_TYPE),
    )
    trigger_entity = entry.options.get(
        CONF_TRIGGER_ENTITY,
        entry.data.get(CONF_TRIGGER_ENTITY),
    )

    runtime = AlprRuRuntime(
        hass=hass,
        entry=entry,
        api=api,
        default_camera=default_camera,
        default_plate_type=default_plate_type,
        trigger_entity=trigger_entity,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    if trigger_entity:
        async def _async_run_automatic_recognition() -> None:
            """Run one automatic recognition and contain failures."""
            try:
                _LOGGER.debug(
                    "Automatic ALPR recognition triggered by %s",
                    trigger_entity,
                )
                await runtime.async_recognize()
            except HomeAssistantError as err:
                _LOGGER.warning(
                    "Automatic ALPR recognition from %s failed: %s",
                    trigger_entity,
                    err,
                )
            finally:
                runtime.trigger_running = False

        @callback
        def _trigger_changed(event) -> None:
            """Schedule recognition when the selected binary sensor turns on."""
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")

            if new_state is None or new_state.state != STATE_ON:
                return
            if old_state is not None and old_state.state == STATE_ON:
                return
            if runtime.trigger_running:
                _LOGGER.debug(
                    "Ignoring trigger %s because recognition is already running",
                    trigger_entity,
                )
                return

            runtime.trigger_running = True
            hass.async_create_task(_async_run_automatic_recognition())

        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                [trigger_entity],
                _trigger_changed,
            )
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an ALPR-RU config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
