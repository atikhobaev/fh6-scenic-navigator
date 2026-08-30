# FH6 Scenic Navigator v1.16.1 — MAP-FIRST PLANNER

Planner — отдельное окно `/planner/` для подготовки маршрута. DRIVE остаётся минималистичным экраном навигации, а PLAN теперь построен вокруг карты.

## 1. Интерфейс

Основная схема:

```text
MAP FILTERS |                 MAP                 | CURRENT ROUTE
            |  Search + marker popover поверх    |
```

Карта занимает большую часть окна. Левая и правая панели можно сворачивать/изменять по ширине; на узком окне они работают как drawers.

## 2. Поиск и слои

Глобальный поиск находится сверху и ищет по **полному каталогу**, включая скрытые слои. Если найденная точка сейчас выключена фильтром, Planner временно показывает только выбранный результат, не меняя сохранённые настройки слоя.

Слои сгруппированы:

- **DISCOVER** — Settlements, Landmarks, Scenic Spots/Roads, Photo Spots, Houses, Festival Sites, Easter Eggs;
- **GAMEPLAY / STORY**;
- **PR STUNTS**;
- **EVENTS**;
- **RACES**;
- **COLLECT / CARS** — Barn Finds, Treasure Cars, Used Cars, Boards, Collectibles и т.д.;
- **COMMUNITY** — Scenic, Secret Roads, Jumps, Easter Eggs, Collectibles, Other;
- **MY** — My Places.

По умолчанию используется спокойный пресет **Recommended**. Кнопки **Enable all / Disable all / Recommended** управляют всеми слоями. Настройки сохраняются в браузере.

Route markers, выбранный marker и Active Route geometry не скрываются фильтрами и не поглощаются обычными clusters.

## 3. Popover на карте

Отдельного экрана Place Details больше нет. Клик по точке открывает anchored popover прямо на карте.

Доступны действия:

- Add to route;
- Set destination;
- Favorite / unfavorite;
- Edit/Delete для My Places.

Если у точки есть локальное изображение, оно отображается в popover. Runtime принимает только пути `/media/places/...`; HTTP(S) изображения запрещены, поэтому Planner не зависит от стороннего сайта во время поездки.

## 4. Built-in Grand Tour Japan

Открой **Saved Routes**. Маршруты разделены на группы:

- **Built-in**;
- **Saved**.

`Grand Tour Japan` — встроенный read-only маршрут из 27 проверенных scenic destinations. Он существует виртуально и не записывается в пользовательскую таблицу `routes` только из-за открытия.

Можно:

- открыть его;
- увидеть все 27 точек и полный Directed-WVAN preview;
- нажать **START NAVIGATION** напрямую.

Если выполнить структурную правку — добавить/удалить/переставить точку, Reverse, Optimize или изменить Scenic direction — Planner сначала создаёт обычный пользовательский маршрут **Grand Tour Japan — Copy**, делает его Active и применяет изменение к копии. Оригинал остаётся неизменным.

## 5. Current Route

Справа Route Items можно:

- переставлять drag&drop;
- двигать `↑ / ↓`;
- удалять;
- раскрывать для дополнительных действий;
- блокировать по позиции;
- для Scenic block фиксировать направление.

После каждого завершённого изменения route revision увеличивается, состояние автоматически сохраняется. `Ctrl+Z` — Undo, `Ctrl+Y` — Redo.

## 6. Работа с картой

- одиночный ЛКМ по POI — выбрать marker и открыть popover;
- двойной ЛКМ по пустой карте — добавить временный waypoint;
- `Shift + ЛКМ` — quick add;
- ПКМ — Set destination / Add waypoint / Add VIA / Save to My Places;
- `Esc` — закрыть popover/drawer/map mode.

## 7. My Places

**ADD PLACE** позволяет:

- выбрать точку на карте;
- взять текущую позицию автомобиля;
- ввести FH6 X/Z вручную.

При сохранении Planner находит ближайший WVAN NavPoint. Marker остаётся в выбранной world-position, а маршрут строится к `nav_anchor_point_id`.

## 8. Community и offline images

В сборке есть два отдельных файла:

```text
static/data/community_evidence.json
static/data/community_places.json
```

`community_evidence.json` — build-time evidence из внешних источников. Запись может содержать название, категорию, contributor, source URL и сведения о screenshot, даже если точные FH6 world coordinates пока недоступны.

`community_places.json` — только runtime-каталог. Точка попадает туда **только когда**:

1. получены явные FH6 world X/Y/Z;
2. координаты проходят проверку;
3. найден валидный WVAN anchor;
4. image, если есть, сохранён локально.

Importer:

```text
scripts/import_forzahorizon_community.py
```

Он не угадывает координаты по screenshot и не делает runtime scraping. Если координат нет — запись остаётся evidence-only.

## 9. START NAVIGATION

Кнопка активна только когда все обязательные directed legs разрешены. При запуске создаётся Navigation Session со статусами `active / upcoming / visited / skipped`.

Planner можно оставить открытым и редактировать маршрут во время поездки; DRIVE получает локальные REST/SSE обновления.

## 10. Fail-closed Directed WVAN

Planner и DRIVE используют authoritative `fh6-navgraph-v1`.

Если legal directed path отсутствует:

- leg получает `Route unavailable`;
- START NAVIGATION отключается;
- Optimize не сохраняет частичный результат;
- приложение **не** переключается на legacy bidirectional `shortestPath()`.

## 11. SQLite и migration v2

Пользовательские данные находятся в:

```text
data/navigator.db
```

v1.16 использует schema version 2. При обновлении базы v1 сначала создаётся копия в:

```text
data/backups/
```

Изменение v2 позволяет Navigation Session ссылаться на virtual built-in route, который намеренно отсутствует в пользовательской таблице `routes`.

## 12. Import / Export

В Planner menu доступны:

- Export / Import user data;
- Export / Import Route;
- diagnostics;
- Show navigation anchors;
- Show directed graph.

Built-in Grand Tour не дублируется в пользовательский backup сам по себе; экспортируется только пользовательская часть данных.
