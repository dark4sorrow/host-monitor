docker build -t host-monitor .

docker stop host-monitor

docker rm host-monitor

docker run -d \
  --name host-monitor \
  --restart unless-stopped \
  -p 5005:5000 \
  -v "$(pwd)/config.json":/app/config.json \
  -v "$(pwd)/output":/app/output \
  host-monitor
