# ALPR-RU for Home Assistant

Облачное распознавание автомобильных номеров для Home Assistant через ALPR-RU.

Интеграция получает текущий кадр из выбранной `camera.*` внутри Home Assistant и отправляет JPEG по HTTPS в ALPR-RU. Камеру не нужно публиковать в интернет, пробрасывать RTSP или открывать порты.

## Установка через HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pirsasha&repository=alpr_ru_homeassistant&category=integration)

После установки перезапустите Home Assistant и добавьте интеграцию:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=alpr_ru)

## Возможности v0.4

- выбор любой сущности `camera.*` в Home Assistant;
- отправка кадра на `https://api-alpr.pirogovx.ru/v1/recognize`;
- ручное распознавание кнопкой или действием `alpr_ru.recognize`;
- автоматический запуск от выбранного `binary_sensor.*` без периодического опроса;
- сенсор последнего номера и диагностические атрибуты;
- камера **«Последний отправленный кадр»**;
- камера **«Последний результат ALPR»** с crop/rectified crop номера;
- белый список автомобильных номеров;
- автоматическое открытие выбранного `switch.*`, `button.*` или `cover.*`;
- минимальная уверенность и cooldown для защиты от повторных команд;
- локальная бренд-иконка Home Assistant.

## Настройка доступа по номеру

Откройте **Настройки → Устройства и службы → ALPR-RU → Настроить**.

Для автоматического доступа можно включить **«Открывать ворота для разрешённых номеров»**, указать номера и выбрать сущность ворот. Номера можно вводить по одному на строку или через пробел/запятую; кириллица и латиница нормализуются перед сравнением.

Поддерживаемые сущности:

- `switch.*` → `turn_on`;
- `button.*` → `press`;
- `cover.*` → `open_cover`.

Автооткрытие по умолчанию выключено. Номер должен точно совпасть с белым списком, иметь корректный формат и пройти настроенный порог уверенности.

## Просмотр кадров

`Последний отправленный кадр` хранится только в памяти Home Assistant и показывает точные байты изображения, отправленные в API.

`Последний результат ALPR` использует debug URL, возвращаемый `/v1/recognize`. Crop скачивается только при первом открытии сущности и затем кэшируется до следующего распознавания.

## Действие для любой камеры

```yaml
action: alpr_ru.recognize
data:
  entity_id: camera.vorota
  plate_type: auto
```

## События

При успешном распознавании:

```text
alpr_ru_plate_detected
```

При успешном открытии ворот разрешённому автомобилю:

```text
alpr_ru_access_granted
```

## Версия

Текущая версия: **0.4.0**. GitHub Release создаётся автоматически при изменении версии в `manifest.json`, поэтому HACS показывает нормальный номер версии вместо SHA коммита.
