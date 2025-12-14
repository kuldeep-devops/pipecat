# Free SSL Setup for EC2 WebSocket Server

## What You'll Get
- ✅ Free SSL certificate (Let's Encrypt)
- ✅ HTTPS frontend
- ✅ WSS (secure WebSocket) 
- ✅ Auto-renewal every 90 days
- ✅ Works in all browsers

## Prerequisites
- EC2 instance running
- A domain name (can use free: freenom.com, or cheap: namecheap.com ~$1/year)
- Domain pointed to EC2 public IP

## Setup Steps

### 1. Point Domain to EC2
```bash
# Get your EC2 public IP
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[PublicIpAddress]' --output text

# Then add A record in your domain DNS:
# Type: A
# Name: voice (or @)
# Value: <YOUR-EC2-IP>
# TTL: 300
```

### 2. Install Nginx and Certbot on EC2
```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-IP>

# Update packages
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Start Docker container (your app on port 8765)
sudo docker run -d -p 8765:8765 --name voice-assistant \
  --env-file .env \
  your-ecr-repo/healthcare-voice-assistant:latest
```

### 3. Configure Nginx for WebSocket
```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/voice-assistant

# Paste this config:
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        # Serve static frontend
        root /var/www/html;
        index index.html;
        try_files $uri $uri/ =404;
    }

    location /ws {
        # WebSocket proxy
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/voice-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Upload frontend
sudo cp /path/to/index.html /var/www/html/
```

### 4. Get Free SSL Certificate
```bash
# Run Certbot (automatic setup)
sudo certbot --nginx -d your-domain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Enable redirect (choose option 2)

# Certbot automatically:
# ✅ Gets certificate
# ✅ Updates Nginx config  
# ✅ Sets up auto-renewal
```

### 5. Update Frontend WebSocket URL
```javascript
// In index.html, update:
let wsUrl = 'wss://your-domain.com/ws';
```

### 6. Test Auto-Renewal
```bash
# Test renewal (dry-run)
sudo certbot renew --dry-run

# If successful, certificate will auto-renew every 90 days
```

## Alternative: Cloudflare Tunnel (Even Easier!)

If you don't want to manage domain/SSL:

```bash
# Install Cloudflare tunnel
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Create tunnel (free account needed)
cloudflared tunnel --url http://localhost:8765

# You'll get: https://random-subdomain.trycloudflare.com
# Use this as your WSS URL!
```

**Pros:** 
- No domain needed
- Instant SSL
- Free

**Cons:**
- Random URL changes each restart
- For demos only, not production

## Cost Summary

| Option | SSL Cost | Domain Cost | Total |
|--------|----------|-------------|-------|
| Let's Encrypt + Domain | FREE | $1-10/year | $1-10/year |
| Cloudflare Tunnel | FREE | FREE | FREE (demo only) |
| AWS ALB + ACM | FREE | $1-10/year | $32/month (ALB cost) |

## Recommended for Demo

**Use Cloudflare Tunnel for quick demo:**
1. Deploy Docker to EC2 (5 min)
2. Run cloudflared tunnel (1 min)
3. Update frontend URL (1 min)
4. Demo ready! (7 minutes total)

Let me know which approach you prefer!
