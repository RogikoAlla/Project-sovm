# King and Servant (Project-sovm)

Многопользовательская консольная карточная игра для **4 игроков** по TCP, Python 3.11+.

## Правила игры

Игра основана на «Дураке» с одним ключевым отличием: **Король (ранг) бьёт Туза (ранг)**.

1. Четырём игрокам раздаётся по 9 карт (колода 36) или по 13 (колода 52).
2. При **первой** раздаче сессии держатель **Короля пик** получает роль **King**; остальные роли — Ace, Queen, Servant — назначаются **против часовой стрелки**. В **каждом следующем раунде** роли **сохраняются** и не перераспределяются, даже если Король пик оказался у другого игрока.
3. Цель: оставаться King как можно дольше; остальные стремятся занять эту роль.
4. **King** один раз за раунд может **слепо обменять** руку с любым игроком.
5. **King** объявляет козырную масть в начале раунда.
6. Атака идёт по часовой: Servant → Queen → Ace → King.
7. Атакующий может **подкидывать** карты того же ранга, что уже на столе; только атакующий подкидывает или объявляет отбой.
8. Если защитник **берёт** карты со стола, роли атакующего и защитника **меняются**. **Исключение:** если **Servant** поднимает карты у **King**, роли **не меняются**.
9. Игрок без карт остаётся неактивным до конца раунда, но **сохраняет роль**.

## Доменный слой

Чистая логика игры (без сети и интерфейса):

| Модуль | Назначение |
|--------|------------|
| `common/models.py` | `Card`, `build_deck`, `PlayerInfo`, `GameState` |
| `server/game_engine.py` | `GameEngine` — раздача, роли, атака/защита, взятие, обмен King |

Подробнее — в Sphinx-документации (`doit docs`) и docstrings модулей.

## Структура проекта

```
Project-sovm/
├── common/          # Константы, модели, протокол, i18n
├── server/          # TCP-сервер + game engine
├── client/          # Консольный клиент
├── tests/           # pytest (≥75% coverage)
├── docs/            # Sphinx (docs/source → docs/build/html)
├── locale/          # Локализация ru/en
├── dodo.py          # Задачи doit: lint, test, docs, locale
└── pyproject.toml
```

## Быстрый старт

```bash
git clone git@github.com:RogikoAlla/Project-sovm.git
cd Project-sovm
pip install -e ".[dev]"
```

### Сервер

```bash
kas-server --deck 36
```

### Клиент (4 терминала)

```bash
kas-client --name Player_name
```

## Задачи разработки (doit)

```bash
doit lint     # flake8 + pydocstyle
doit test     # pytest с coverage
doit docs     # Sphinx HTML → docs/build/html
doit locale   # компиляция переводов
```

## Документация

```bash
doit docs
# открыть docs/build/html/index.html
```

API других модулей (protocol, server, client) подтягивается через ``automodule``
из docstrings, которые пишут авторы соответствующих частей.

## Требования

- Python ≥ 3.11
- Dev: pytest, pytest-cov, sphinx, flake8, pydocstyle, doit, build
