# Данные

В репозитории хранится исходный файл A/B-теста `raw/ab_test.csv` (404 770 строк),
полученный по [публичной ссылке из задания](https://disk.yandex.ru/d/SOkIsD5A8xlI7Q).

Два файла первого задания не добавлены в Git из-за размера:

- `problem1-reg_data.csv` — 1 000 000 регистраций, около 17 МБ;
- `problem1-auth_data.csv` — 9 601 013 авторизаций, около 162 МБ.

В текущей версии ноутбука указаны пути владельца проекта:

```python
REG_PATH = Path('/Users/yaroslavzinchenko/Downloads/problem1-reg_data.csv')
AUTH_PATH = Path('/Users/yaroslavzinchenko/Downloads/problem1-auth_data.csv')
AB_PATH = Path('/Users/yaroslavzinchenko/Downloads/Проект_1_Задание_2.csv')
```

На другом компьютере нужно изменить только эти три строки.

На GitHub сохранены все выполненные ячейки, таблицы и графики анализа полного датасета.
