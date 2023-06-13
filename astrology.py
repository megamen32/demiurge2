def natal_map():
    from kerykeion import KrInstance,print_all_data,Report

    # Создайте экземпляр kerykeion:
    ekaterina = KrInstance("Ekaterina", 1997, 4, 25, 11, 42, "Bryansk")

    # Получите информацию о Солнце в карте:
    print(ekaterina.sun)

    # Получите информацию о Луне в карте:
    print(ekaterina.moon)

    # Получите информацию о Венере в карте:
    print(ekaterina.venus)

    # Получите информацию о первом доме:
    print(ekaterina.first_house)

    # Получите элемент знака Луны:
    print(ekaterina.moon.get("element"))
def planetpos():
    import swisseph as swe
    import datetime

    # Устанавливаем путь к эфемеридам
    swe.set_ephe_path("/usr/share/ephe")

    # Определяем сегодняшнюю дату
    now = datetime.datetime.now()

    # Преобразуем дату в формат Julian Day
    jd = swe.julday(now.year, now.month, now.day)

    # Планеты, которые мы хотим рассмотреть
    planets = {'Sun': swe.SUN, 'Moon': swe.MOON, 'Venus': swe.VENUS}

    # Вычисляем положение планет
    positions = {}
    for planet, id in planets.items():
        position, ret = swe.calc_ut(jd, id)
        positions[planet] = position

    print(positions)
