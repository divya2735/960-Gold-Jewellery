from django.apps import AppConfig


class App1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app1'


class YourappConfig(AppConfig):  # Replace 'Yourapp' with your app name
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'yourapp'  # Replace with your app name
    
    def ready(self):
        """Start scheduler when app loads"""
        from apscheduler.schedulers.background import BackgroundScheduler
        from .views import update_gold_price_daily
        import logging
        
        logger = logging.getLogger(__name__)
        
        scheduler = BackgroundScheduler()
        
        # Schedule task to run at 8 AM every day
        scheduler.add_job(
            update_gold_price_daily,
            'cron',
            hour=8,
            minute=0,
            id='update_gold_price',
            name='Update Gold Price Daily',
            replace_existing=True
        )
        
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ Gold price scheduler started!")