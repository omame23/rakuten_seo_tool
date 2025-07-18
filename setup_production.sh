#!/bin/bash

echo "Setting up production environment..."

# 1. Create log directory
sudo mkdir -p /var/log/inspice
sudo chown www-data:www-data /var/log/inspice

# 2. Create Celery PID directory
sudo mkdir -p /var/run/celery
sudo chown www-data:www-data /var/run/celery

# 3. Install Gunicorn
cd /var/www/inspice/rakuten_seo_tool
source venv/bin/activate
pip install gunicorn

# 4. Change ownership of project directory
sudo chown -R www-data:www-data /var/www/inspice/rakuten_seo_tool

# 5. Copy systemd service files
sudo cp inspice.service /etc/systemd/system/
sudo cp inspice-celery.service /etc/systemd/system/
sudo cp inspice-celery-beat.service /etc/systemd/system/

# 6. Reload systemd daemon
sudo systemctl daemon-reload

# 7. Enable services
sudo systemctl enable inspice
sudo systemctl enable inspice-celery
sudo systemctl enable inspice-celery-beat

# 8. Start services
sudo systemctl start inspice
sudo systemctl start inspice-celery
sudo systemctl start inspice-celery-beat

echo "Production setup complete!"
echo "Check service status with:"
echo "  sudo systemctl status inspice"
echo "  sudo systemctl status inspice-celery"
echo "  sudo systemctl status inspice-celery-beat"