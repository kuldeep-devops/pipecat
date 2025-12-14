# 🚀 AWS EC2 Deployment Guide

Complete guide for deploying the **Healthcare Voice Assistant** to AWS EC2 with free SSL support.

---

## ✅ Prerequisites
1. **AWS Account**: Login to aws.amazon.com
2. **API Keys**: Have your DEEPGRAM_API_KEY, OPENAI_API_KEY, and ELEVENLABS_API_KEY ready
3. **Domain (Optional)**: Can use Cloudflare Tunnel for free SSL without domain

---

## Quick Demo with Cloudflare Tunnel (10 minutes)

### Step 1: Launch EC2 Instance

1. Go to EC2 Console in AWS
2. Click "Launch Instance"
3. Configure:
   - Name: voice-assistant-server
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t3.small
   - Security Group: Allow ports 22, 80, 443, 8765
4. Launch and note the Public IP

### Step 2: Setup Docker

```bash
ssh -i your-key.pem ubuntu@<EC2-IP>
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
exit
```

### Step 3: Run Container

```bash
git clone https://github.com/your-repo/healthcare-voice-assistant.git
cd healthcare-voice-assistant

# Create .env
cat > .env <<EOF
DEEPGRAM_API_KEY=your_key
OPENAI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
SERVER_HOST=0.0.0.0
SERVER_PORT=8765
ALLOWED_ORIGINS=*
EOF

docker build -t voice-assistant .
docker run -d --name voice-assistant --restart unless-stopped -p 8765:8765 --env-file .env voice-assistant
```

### Step 4: Setup FREE SSL with Cloudflare

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
cloudflared tunnel --url http://localhost:8765
# Copy the https://random.trycloudflare.com URL
```

### Step 5: Update Frontend

Update client/index.html:
```javascript
let wsUrl = 'wss://random.trycloudflare.com';
```

Upload and serve:
```bash
scp -i your-key.pem client/index.html ubuntu@<EC2-IP>:~/
ssh -i your-key.pem ubuntu@<EC2-IP>
python3 -m http.server 8000
```

Access: http://<EC2-IP>:8000

---

## Production with Let's Encrypt (with domain)

Follow Steps 1-3 above, then:

### Get Domain
- Buy from Namecheap ($1/year)
- Point A record to EC2 IP

### Install Nginx + SSL

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo nano /etc/nginx/sites-available/voice-assistant
```

Config:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /var/www/html;
        index index.html;
    }
    
    location /ws {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/voice-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d your-domain.com
```

Deploy:
```bash
sudo cp client/index.html /var/www/html/
```

Update wsUrl to: wss://your-domain.com/ws

Access: https://your-domain.com

---

## Cost: $15/month (EC2 t3.small) + SSL FREE
