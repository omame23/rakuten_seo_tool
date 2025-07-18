#!/bin/bash

echo "Setting up Redis service..."

# 1. Create redis user if it doesn't exist
sudo useradd -r -s /bin/false redis 2>/dev/null || true

# 2. Create Redis configuration directory
sudo mkdir -p /etc/redis

# 3. Create Redis configuration file
sudo tee /etc/redis/redis.conf > /dev/null <<EOF
bind 127.0.0.1
port 6380
timeout 0
tcp-keepalive 0
loglevel notice
logfile /var/log/redis/redis.log
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis
maxmemory-policy allkeys-lru
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
EOF

# 4. Create Redis directories
sudo mkdir -p /var/lib/redis
sudo mkdir -p /var/log/redis

# 5. Set permissions
sudo chown redis:redis /var/lib/redis
sudo chown redis:redis /var/log/redis
sudo chmod 750 /var/lib/redis
sudo chmod 750 /var/log/redis

# 6. Copy systemd service file
sudo cp redis.service /etc/systemd/system/

# 7. Reload systemd daemon
sudo systemctl daemon-reload

# 8. Enable and start Redis service
sudo systemctl enable redis
sudo systemctl start redis

echo "Redis service setup complete!"
echo "Check Redis status with: sudo systemctl status redis"