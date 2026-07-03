import re
from datetime import datetime, timedelta


def parse_task(text: str) -> tuple | None:
    text = text.strip()
    if not text:
        return None

    repeat_type = _extract_repeat_type(text)

    dt = _extract_datetime(text)
    if not dt:
        return None

    task_text = _clean_text(text, dt)
    if not task_text:
        return None

    return dt, task_text, repeat_type


def _extract_datetime(text: str) -> datetime | None:
    now = datetime.now()
    text_lower = text.lower()

    r = _try_relative(text_lower, now)
    if r:
        return r

    r = _try_full_date(text, now)
    if r:
        return r

    r = _try_day_month(text, now)
    if r:
        return r

    r = _try_day_only(text, now)
    if r:
        return r

    r = _try_time_only(text, now)
    if r:
        return r

    return None


def _extract_time(text: str) -> tuple[int, int] | None:
    m = re.search(r'(\d{1,2})\s*[:.]\s*(\d{2})', text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return h, mi
    return None


def _extract_repeat_type(text: str) -> str | None:
    text_lower = text.lower()
    if re.search(r'кажд(?:ый|ой|ую|ое)\s+день|ежедневно|все\s+дни|постоянно', text_lower):
        return "daily"
    if re.search(r'кажд(?:ую|ой)\s+неделю|еженедельно|по\s+(?:понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье| будням| выходным)', text_lower):
        return "weekly"
    if re.search(r'кажд(?:ый|ой|ое)\s+месяц|ежемесячно', text_lower):
        return "monthly"
    return None


def _try_relative(text: str, now: datetime) -> datetime | None:
    time_part = _extract_time(text)

    if 'послезавтра' in text:
        base = now.date() + timedelta(days=2)
        if time_part:
            return datetime.combine(base, datetime.min.time().replace(hour=time_part[0], minute=time_part[1]))
        return datetime.combine(base, datetime.min.time().replace(hour=9))

    if 'завтра' in text:
        base = now.date() + timedelta(days=1)
        if time_part:
            return datetime.combine(base, datetime.min.time().replace(hour=time_part[0], minute=time_part[1]))
        return datetime.combine(base, datetime.min.time().replace(hour=9))

    m = re.search(r'через\s+(\d+)\s*(мин(?:ут[уы]?)?|час(?:ов|а)?|дн(?:ей|я)?)', text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if 'мин' in unit:
            return now + timedelta(minutes=n)
        if 'час' in unit:
            return now + timedelta(hours=n)
        if 'дн' in unit:
            return now + timedelta(days=n)

    return None


def _try_full_date(text: str, now: datetime) -> datetime | None:
    m = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})', text)
    if not m:
        return None

    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None

    time_part = _extract_time(text)
    if time_part:
        try:
            return datetime(year, month, day, time_part[0], time_part[1])
        except ValueError:
            return None

    try:
        return datetime(year, month, day, 9, 0)
    except ValueError:
        return None


def _try_day_month(text: str, now: datetime) -> datetime | None:
    months = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
        'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
        'май': 5, 'июн': 6, 'июл': 7, 'авг': 8,
        'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
    }

    m = re.search(r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)', text, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month = months[m.group(2).lower()]
        year = now.year
        if not (1 <= day <= 31):
            return None
        time_part = _extract_time(text)
        if time_part:
            try:
                dt = datetime(year, month, day, time_part[0], time_part[1])
            except ValueError:
                return None
        else:
            try:
                dt = datetime(year, month, day, 9, 0)
            except ValueError:
                return None
        if dt < now:
            dt = dt.replace(year=year + 1)
        return dt

    return None


def _try_day_only(text: str, now: datetime) -> datetime | None:
    time_part = _extract_time(text)
    if not time_part:
        return None

    m = re.search(r'(?:^|\s)(\d{1,2})(?:\s|числ[ао]|го\s)', text)
    if not m:
        m = re.search(r'(?:^|\s)(\d{1,2})\s', text)
    if not m:
        return None

    day = int(m.group(1))
    if not (1 <= day <= 31):
        return None

    dt = now.replace(hour=time_part[0], minute=time_part[1], second=0, microsecond=0)
    if day <= now.day:
        if now.month == 12:
            dt = dt.replace(year=now.year + 1, month=1, day=day)
        else:
            dt = dt.replace(month=now.month + 1, day=day)
    else:
        dt = dt.replace(day=day)

    if dt < now:
        dt += timedelta(days=1)

    return dt


def _try_time_only(text: str, now: datetime) -> datetime | None:
    time_part = _extract_time(text)
    if not time_part:
        return None

    dt = now.replace(hour=time_part[0], minute=time_part[1], second=0, microsecond=0)
    if dt <= now:
        dt += timedelta(days=1)
    return dt


def _clean_text(text: str, dt: datetime) -> str:
    t = text

    t = re.sub(r'кажд(?:ый|ой|ую|ое)\s+день|ежедневно|все\s+дни|постоянно', '', t, flags=re.IGNORECASE)
    t = re.sub(r'кажд(?:ую|ой)\s+неделю|еженедельно', '', t, flags=re.IGNORECASE)
    t = re.sub(r'кажд(?:ый|ой|ое)\s+месяц|ежемесячно', '', t, flags=re.IGNORECASE)
    t = re.sub(r'по\s+(?:понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье|будням|выходным)', '', t, flags=re.IGNORECASE)

    t = re.sub(r'послезавтра', '', t, flags=re.IGNORECASE)
    t = re.sub(r'завтра', '', t, flags=re.IGNORECASE)
    t = re.sub(r'через\s+\d+\s*(?:минут[уы]?|час(?:ов|а)?|дн(?:ей|я)?)', '', t, flags=re.IGNORECASE)

    t = re.sub(r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', '', t)

    months = 'января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек'
    t = re.sub(rf'\d{{1,2}}\s+(?:{months})', '', t, flags=re.IGNORECASE)

    t = re.sub(r'\d{1,2}\s*[:.]\s*\d{2}', '', t)
    t = re.sub(r'\d{1,2}\s+числ[ао]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\d{1,2}\s+го\b', '', t, flags=re.IGNORECASE)

    t = re.sub(r'^\d{1,2}\s+', '', t)

    t = re.sub(r'\bнапомни(?:ть)?\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bнапоминание\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bнужно\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bнадо\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bпро\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bчто\s+в\b', '', t, flags=re.IGNORECASE)

    t = re.sub(r'\bв\b\s*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^\s*в\b\s*', '', t, flags=re.IGNORECASE)

    t = re.sub(r'\s+', ' ', t).strip(' ,-–:.')

    return t
