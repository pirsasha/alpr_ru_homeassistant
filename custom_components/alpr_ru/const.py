"""Constants for the ALPR-RU integration."""

from homeassistant.const import Platform

DOMAIN = "alpr_ru"

CONF_API_URL = "api_url"
CONF_API_KEY = "api_key"
CONF_CAMERA_ENTITY = "camera_entity"
CONF_PLATE_TYPE = "plate_type"

DEFAULT_API_URL = "https://alpr.pirogovx.ru/api"
DEFAULT_PLATE_TYPE = "auto"
PLATE_TYPES = ["auto", "single_line", "two_line"]

SERVICE_RECOGNIZE = "recognize"
EVENT_PLATE_DETECTED = "alpr_ru_plate_detected"

SIGNAL_RESULT = f"{DOMAIN}_result_{{entry_id}}"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]
