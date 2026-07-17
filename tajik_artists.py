# Known Tajik & Uzbek artists on Deezer
# Format: (latin_name, cyrillic_name, deezer_id_if_known)

TAJIK_ARTISTS = [
    ("Rustam Azimi", "Рустам Азими"),
    ("Bahrom Gafuri", "Бахром Гафури"),
    ("Shabnami Surayo", "Шабнам Сурайё"),
    ("Shabnam Surayo", "Шабнам Сурё"),
    ("Bakhtiyor Ibrohimov", "Бахтиёр Ибрагимов"),
    ("Farhod Oripov", "Фарход Орипов"),
    ("Maryam Jalolova", "Мариям Жалолова"),
    ("Daler Ruz", "Далер Руз"),
    ("Ziyo", "Зиё"),
    ("Sadriddin Burhonov", "Садриддин Бурҳонов"),
    ("Mekhron Khasanov", "Мехрон Хасанов"),
    ("Farhod Dustov", "Фарход Дустов"),
    ("Shahnoza", "Шахноза"),
    ("Firooz", "Фирӯз"),
]

UZBEK_ARTISTS = [
    ("Otabek Mutalibov", "Отабек Муталибов"),
    ("Sherali Jo'rayev", "Шерали Жўраев"),
    ("Yulduz Usmonova", "Юлдуз Усмонова"),
    ("Sardor Rahimhon", "Сардор Рахимхон"),
    ("Hulkar Abdullayeva", "Хулкар Абдуллаева"),
    ("Ozoda Nursaidova", "Озада Нурсаидова"),
    ("Sobir Umarov", "Собир Умаров"),
    ("Habib Sharipov", "Хабиб Шарипов"),
    ("Kamoliddin Rahimov", "Камолиддин Рахимов"),
    ("Ozoda", "Озода"),
    ("Rayhon", "Райхон"),
    ("Munisa Rizayeva", "Муниса Ризаева"),
    ("Shahzoda", "Шахзода"),
    ("Nilufar Usmonova", "Нилуфар Усмонова"),
    ("Akbar Abdullaev", "Акбар Абдуллаев"),
]

ALL_CENTRAL_ASIAN = TAJIK_ARTISTS + UZBEK_ARTISTS

# Popular Tajik/Uzbek songs to try in random
POPULAR_SONGS = [
    ("Afsus", "Rustam Azimi"),
    ("Umri Mo", "Bahrom Gafuri"),
    ("Chaki Chaki Boron", "Shabnami Surayo"),
    ("Maro makush", "Bahrom Gafuri"),
    ("Dustat Doram", "Shabnam Surayo"),
    ("Modari Khubam", "Sirojiddin Fozilov"),
    ("Ajab Shirini", "Rustam Azimi"),
]


def get_search_variants(query: str) -> list[str]:
    """Generate search variants for Tajik/Uzbek queries"""
    variants = [query]
    query_lower = query.lower().strip()

    for latin, cyrillic in ALL_CENTRAL_ASIAN:
        if query_lower in cyrillic.lower() or cyrillic.lower() in query_lower:
            variants.append(latin)
        elif query_lower in latin.lower() or latin.lower() in query_lower:
            variants.append(cyrillic)

    return list(dict.fromkeys(variants))
