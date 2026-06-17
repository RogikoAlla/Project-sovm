common package
==============

Submodules
----------

common.constants module
-----------------------

.. automodule:: common.constants
   :members:
   :show-inheritance:
   :undoc-members:

common.i18n module
------------------

.. automodule:: common.i18n
   :members:
   :show-inheritance:
   :undoc-members:

common.models module
--------------------

Модели доменного слоя — чистые структуры данных без сети и UI:

* **Card** — неизменяемая карта (ранг + масть). Сравнение по правилам Durak
  с особенностью KAS: **Король сильнее Туза**. Сериализация ``to_dict`` /
  ``from_dict`` для протокола.
* **build_deck** — построение и перемешивание колоды 36 или 52 карт.
* **PlayerInfo** — публичное представление игрока (роль, размер руки без
  раскрытия карт).
* **GameState** — снимок состояния для клиента: стол, козырь, текущий
  атакующий/защитник, приватная рука получателя.

.. automodule:: common.models
   :members:
   :show-inheritance:
   :undoc-members:

common.protocol module
----------------------

.. automodule:: common.protocol
   :members:
   :show-inheritance:
   :undoc-members:

Module contents
---------------

.. automodule:: common
   :members:
   :show-inheritance:
   :undoc-members:
