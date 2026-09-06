"""Constants for the ALPR-RU integration."""

from homeassistant.const import Platform

DOMAIN = "alpr_ru"
INTEGRATION_VERSION = "0.4.1"

CONF_API_URL = "api_url"
CONF_API_KEY = "api_key"
CONF_CAMERA_ENTITY = "camera_entity"
CONF_TRIGGER_ENTITY = "trigger_entity"
CONF_PLATE_TYPE = "plate_type"

CONF_ACCESS_ENABLED = "access_enabled"
CONF_ALLOWED_PLATES = "allowed_plates"
CONF_GATE_ENTITY = "gate_entity"
CONF_MIN_CONFIDENCE = "min_confidence"
CONF_GATE_COOLDOWN = "gate_cooldown"

DEFAULT_API_URL = "https://api-alpr.pirogovx.ru"
DEFAULT_PLATE_TYPE = "auto"
DEFAULT_ACCESS_ENABLED = False
DEFAULT_ALLOWED_PLATES = ""
DEFAULT_MIN_CONFIDENCE = 0.85
DEFAULT_GATE_COOLDOWN = 30
PLATE_TYPES = ["auto", "single_line", "two_line"]

SERVICE_RECOGNIZE = "recognize"
EVENT_PLATE_DETECTED = "alpr_ru_plate_detected"
EVENT_ACCESS_GRANTED = "alpr_ru_access_granted"

SIGNAL_RESULT = f"{DOMAIN}_result_{{entry_id}}"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.CAMERA]
