from datetime import date


def register(app):
    @app.context_processor
    def inject_today():
        today = date.today()
        return {
            'current_date': today.isoformat(),
            'current_year': today.year,
            'current_month': today.month,
            'current_day': today.day,
            'days': range(1, 32),
            'months': [
                (1, 'Gener'), (2, 'Febrer'), (3, 'Març'), (4, 'Abril'),
                (5, 'Maig'), (6, 'Juny'), (7, 'Juliol'), (8, 'Agost'),
                (9, 'Setembre'), (10, 'Octubre'), (11, 'Novembre'), (12, 'Desembre')
            ],
            'years': range(2024, 2031)
        }

    @app.template_filter('format_date')
    def format_date_filter(s):
        if not s: return ""
        # Try to parse ISO date (YYYY-MM-DD)
        try:
            if ' ' in s: # Timestamp format: 2026-04-08 12:30:00
                date_part = s.split(' ')[0]
                y, m, d = date_part.split('-')
                time_part = s.split(' ')[1][:5] # HH:MM
                return f"{d}/{m}/{y} {time_part}"
            else: # Date format: 2026-04-08
                y, m, d = s.split('-')
                return f"{d}/{m}/{y}"
        except:
            return s

    @app.template_filter('minutes_to_time')
    def minutes_to_time_filter(minutes):
        if minutes is None: return ""
        try:
            minutes = int(minutes)
            return f"{minutes // 60:02d}:{minutes % 60:02d}"
        except (ValueError, TypeError):
            return ""

    @app.template_filter('seconds_to_duration')
    def seconds_to_duration_filter(seconds):
        if seconds is None: return ""
        try:
            seconds = int(seconds)
            h, rem = divmod(seconds, 3600)
            m = rem // 60
            return f"{h}h {m:02d}m" if h else f"{m}m"
        except (ValueError, TypeError):
            return ""
