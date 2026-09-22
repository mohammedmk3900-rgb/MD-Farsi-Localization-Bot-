from __future__ import annotations


MILESTONES = {
    1: ("🎉", "اولین ۱٪", "اولین نقطه عطف ترجمه ثبت شد."),
    10: ("🌱", "۱۰٪ — آغاز جدی", "ده درصد مسیر ترجمه پشت سر گذاشته شد."),
    25: ("📈", "۲۵٪ — یک‌چهارم مسیر", "یک‌چهارم پروژه ترجمه شده است."),
    50: ("🔥", "۵۰٪ — نیمه راه", "پروژه به نیمه مسیر ترجمه رسید."),
    75: ("🚀", "۷۵٪ — نزدیک به پایان", "بخش بزرگی از ترجمه تکمیل شده است."),
    100: ("🏁", "۱۰۰٪ — تکمیل ترجمه", "ترجمه پروژه به پایان رسید."),
}


class AchievementService:
    def crossed(self, previous: float, current: float) -> list[dict]:
        return [
            {"percent": level, "icon": data[0], "title": data[1], "description": data[2]}
            for level, data in MILESTONES.items()
            if previous < level <= current
        ]
