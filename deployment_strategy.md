# ☁️ AWS Deployment Strategy

## Overview
We will deploy the application using modern, managed services to minimize maintenance and ensure security (SSL/TLS) is handled automatically.

-   **Backend**: AWS App Runner (Serverless container runner)
-   **Frontend**: AWS Amplify (Static site hosting)
-   **Database**: None (Stateless)

## 1. Backend Deployment (AWS App Runner)
We will containerize the Python backend and deploy it to App Runner. App Runner automatically handles load balancing and SSL (HTTPS/WSS) endpoints.

### Steps:
1.  **Dockerize**: Create a `Dockerfile` for the python server.
2.  **Push**: Push the code to a GitHub repository.
3.  **Deploy**: Connect AWS App Runner to the GitHub repo.
    -   **Runtime**: Python 3.10+ (or use the Dockerfile mode).
    -   **Port**: 8765
    -   **Env Vars**: Add DEEPGRAM_API_KEY, OPENAI_API_KEY, ELEVENLABS_API_KEY.
4.  **Result**: You get a secure URL like `wss://your-app-id.awsapprunner.com`.

### Local Verification (Optional but Recommended)
Before deploying, you can build and run the Docker container locally to ensure everything is packaged correctly.

**Build the image:**
```bash
docker build -t healthcare-assistant-backend .
```

**Run the container:**
(Make sure to pass your API keys!)
```bash
docker run -p 8765:8765 \
  --env-file .env \
  healthcare-assistant-backend
```

## 2. Frontend Deployment (AWS Amplify)
Amplify is the easiest way to host the static `client/index.html` and assets.

### Steps:
1.  **Preparation**: Ensure `client/index.html` uses the production WebSocket URL (we will make this configurable).
2.  **Deploy**:
    -   Go to AWS Amplify Console.
    -   "Host a web app" -> Connect GitHub.
    -   Point to the `client` folder.
3.  **Result**: You get a secure URL like `https://main.app-id.amplifyapp.com`.

## 3. Required Code Changes
### Dockerfile
We need to add a `Dockerfile` to the root directory to define the backend environment.

### Frontend Configuration (Injecting URL)
Since `client/index.html` is a static file, we cannot read environment variables at runtime. Instead, we use a placeholder `__WEBSOCKET_URL__` and replace it during the build process.

**In AWS Amplify Console:**
1.  Go to **Environment variables**.
2.  Add a variable:
    -   Key: `WEBSOCKET_URL`
    -   Value: `wss://<your-app-runner-url>` (e.g., `wss://xyz.awsapprunner.com`)

3.  Go to **Build settings**.
4.  Add this command to the `preBuild` or `build` phase in `amplify.yml`:
    ```yaml
    - sed -i "s|__WEBSOCKET_URL__|$WEBSOCKET_URL|g" client/index.html
    ```
    *(This command finds the placeholder string and replaces it with your actual environment variable value).*

## Cost Estimates (Rough)
-   **App Runner**: ~$5/month (requests) + provisioned instances (pauses when idle in some configs, but persistent connection needs active instance). ~$25/month for 1 active instance 24/7.
-   **Amplify**: Free tier eligible (generous limits).

## Alternative: EC2 (Cheaper, More Manual)
If you prefer a lower cost (Free Tier eligible) but more manual setup:
1.  Launch **t3.micro** instance.
2.  Install Docker.
3.  Run the container.
4.  Install **Caddy** or **Nginx** for SSL (critical for microphone permission).
