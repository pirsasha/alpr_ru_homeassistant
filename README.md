# ALPR-RU for Home Assistant

Облачное распознавание автомобильных номеров для Home Assistant через ALPR-RU.

Интеграция получает текущий кадр из выбранной `camera.*` внутри Home Assistant и отправляет JPEG по HTTPS в ALPR-RU. Камеру не нужно публиковать в интернет, пробрасывать RTSP или открывать порты.

## Установка через HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pirsasha&repository=alpr_ru_homeassistant&category=integration)

После установки перезапустите Home Assistant и добавьте интеграцию:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=alpr_ru)

## Возможности v0.3

- выбор любой сущности `camera.*` в Home Assistant;
- получение JPEG штатным Camera API Home Assistant;
- отправка кадра на `https://api-alpr.pirogovx.ru/v1/recognize`;
- авторизация через API key;
- режимы `auto`, `single_line`, `two_line`;
- сенсор последнего распознанного номера;
- кнопка «Распознать сейчас»;
- действие `alpr_ru.recognize` для распознавания с любой другой камеры;
- событие `alpr_ru_plate_detected` при успешном распознавании;
- автоматический запуск от любого `binary_sensor.*`;
- камера **«Последний отправленный кадр»** — показывает точные байты изображения, которые Home Assistant отправил в ALPR-RU;
- камера **«Последний результат ALPR»** — показывает rectified/crop номера, который вернул ALPR-RU для OCR.

## Просмотр кадров

После первого распознавания в устройстве ALPR-RU появляются две camera-сущности:

```text
Последний отправленный кадр
Последний результат ALPR
```

`Последний отправленный кадр` хранится только в памяти Home Assistant и не записывается в `/config`.

`Последний результат ALPR` использует debug URL, уже возвращаемый ответом `/v1/recognize`. Сам crop загружается с ALPR-RU только при первом просмотре этой camera-сущности и затем кэшируется в памяти до следующего распознавания. Поэтому обычное распознавание не создаёт дополнительного GET-запроса.

Если ALPR не обнаружил номер и crop отсутствует, камера результата будет недоступна до следующего успешного обнаружения.

## Настройка

После установки откройте **Настройки → Устройства и службы → ALPR-RU → Настроить**.

Можно выбрать:

- камеру Home Assistant;
- необязательный `binary_sensor.*` как автоматический триггер;
- тип номера.

Если выбран триггер, интеграция слушает переход датчика из `off` в `on`. При срабатывании она автоматически получает текущий кадр с выбранной камеры и отправляет его в ALPR-RU.

Пример:

```text
binary_sensor: off -> on
        ↓
camera.main -> текущий JPEG
        ↓
ALPR-RU
        ↓
T868EO761
```

Важно: если сама интеграция камеры никогда не переводит выбранный `binary_sensor` в `on`, автоматический запрос не произойдёт. В таком случае нужно выбрать другой реально срабатывающий датчик или использовать ручное действие.

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
trigger_entity: binary_sensor.smart_motion_vehicle
plate: T868EO761
confidence: 0.94
valid_format: true
detector_confidence: 0.91
bbox: [548, 390, 629, 441]
```

## Версия

`0.3.0` добавляет визуальную диагностику: последний отправленный кадр и последний crop/rectified crop, использованный ALPR-RU.
