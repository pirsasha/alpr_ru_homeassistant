# ALPR-RU for Home Assistant

Облачное распознавание автомобильных номеров для Home Assistant через ALPR-RU.

Интеграция получает текущий кадр из выбранной `camera.*` внутри Home Assistant и отправляет JPEG по HTTPS в ALPR-RU. Камеру не нужно публиковать в интернет, пробрасывать RTSP или открывать порты.

## Установка через HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pirsasha&repository=alpr_ru_homeassistant&category=integration)

После установки перезапустите Home Assistant и добавьте интеграцию:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=alpr_ru)

## Возможности v0.1

- выбор любой сущности `camera.*` в Home Assistant;
- получение JPEG штатным Camera API Home Assistant;
- отправка кадра на `https://alpr.pirogovx.ru/api/v1/recognize`;
- авторизация через API key;
- режимы `auto`, `single_line`, `two_line`;
- сенсор последнего распознанного номера;
- кнопка «Распознать сейчас»;
- действие `alpr_ru.recognize` для распознавания с любой другой камеры;
- событие `alpr_ru_plate_detected` при успешном распознавании.

## Настройка

После установки откройте **Настройки → Устройства и службы → Добавить интеграцию → ALPR-RU**.

Укажите:

- API URL: `https://alpr.pirogovx.ru/api`
- API key
- камеру Home Assistant
- тип номера

При сохранении интеграция получает тестовый кадр с камеры и проверяет запрос к ALPR-RU.

## Действие для любой камеры

```yaml
action: alpr_ru.recognize
data:
  entity_id: camera.vorota
  plate_type: auto
```

Камера должна существовать в Home Assistant как сущность `camera.*` и позволять Home Assistant получить текущий кадр.

## Событие

При успешном распознавании возникает событие:

```text
alpr_ru_plate_detected
```

Пример данных:

```yaml
camera_entity: camera.vorota
plate: T868EO761
confidence: 0.94
valid_format: true
detector_confidence: 0.91
bbox: [548, 390, 629, 441]
```

## Статус

Версия `0.1.0` предназначена для первого полевого тестирования на разных интеграциях камер Home Assistant.
