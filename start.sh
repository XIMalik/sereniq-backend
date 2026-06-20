gunicorn sereniq.wsgi:application -b :1001 --workers=6 -t 60 --worker-connections=100 --reload --capture-output --log-level=info
