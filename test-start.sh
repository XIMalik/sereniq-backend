set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn sereniq.wsgi:application \
  --bind 0.0.0.0:${PORT:-10000} \
  --workers ${WEB_CONCURRENCY:-3} \
  --timeout 60 \
  --capture-output \
  --log-level info