from datetime import datetime, date, timedelta

def current_year(request):   
    return {
        'year': datetime.now().year,
        'date_today' : date.today(),
        'date_yesterday': (date.today()) - timedelta(days = 1)}

