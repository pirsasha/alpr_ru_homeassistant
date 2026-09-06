"""Config flow for ALPR-RU."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.camera import async_get_image
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlprRuApi, AlprRuAuthError, AlprRuConnectionError
from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    CONF_CAMERA_ENTITY,
    CONF_PLATE_TYPE,
    DEFAULT_API_URL,
    DEFAULT_PLATE_TYPE,
    DOMAIN,
    PLATE_TYPES,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_API_URL,
                default=values.get(CONF_API_URL, DEFAULT_API_URL),
            ): str,
            vol.Required(CONF_API_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_CAMERA_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="camera")
            ),
            vol.Required(
                CONF_PLATE_TYPE,
                default=values.get(CONF_PLATE_TYPE, DEFAULT_PLATE_TYPE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=PLATE_TYPES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="plate_type",
                )
            ),
        }
    )


class AlprRuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle ALPR-RU config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set up ALPR-RU and validate both camera capture and API key."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            api_url = user_input[CONF_API_URL].strip().rstrip("/")
            api_key = user_input[CONF_API_KEY].strip()
            camera_entity = user_input[CONF_CAMERA_ENTITY]
            plate_type = user_input[CONF_PLATE_TYPE]

            try:
                image = await async_get_image(self.hass, camera_entity, timeout=15)
                api = AlprRuApi(async_get_clientsession(self.hass), api_url, api_key)
                test_result = await api.async_recognize(
                    image.content,
                    image.content_type,
                    plate_type,
                )
            except AlprRuAuthError:
                errors["base"] = "invalid_auth"
            except AlprRuConnectionError as err:
                errors["base"] = "cannot_connect"
                description_placeholders["error"] = str(err)[:200]
            except Exception as err:
                errors["base"] = "cannot_get_camera_image"
                description_placeholders["error"] = str(err)[:200]
            else:
                user_input[CONF_API_URL] = api_url
                user_input[CONF_API_KEY] = api_key
                plate = str(test_result.get("plate") or "").strip()
                title = "ALPR-RU"
                if plate:
                    title = f"ALPR-RU ({plate})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
            description_placeholders=description_placeholders,
        )
