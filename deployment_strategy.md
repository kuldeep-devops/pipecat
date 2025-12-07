# 🚀 AWS Deployment Guide (Step-by-Step)

This guide is designed for anyone to deploy the **HealthCare Voice Assistant** to the cloud. You do not need to be a developer to follow these steps.

---

## ✅ Prerequisites
1.  **AWS Account**: Login to [aws.amazon.com](https://aws.amazon.com).
2.  **GitHub Account**: Ensure this code is pushed to your GitHub repository.
3.  **API Keys**: Have your `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, and `ELEVENLABS_API_KEY` ready.

---

## Part 1: Deploy Backend (AWS App Runner)
*This runs the "Brain" of the AI (Python Server).*

1.  **Go to AWS App Runner**: Search for "App Runner" in the AWS search bar.
2.  **Click "Create service"**.
3.  **Source & Repository**:
    *   **Repository type**: Select "Source code repository".
    *   **Provider**: Select "GitHub" (Connect your account if needed).
    *   **Repository**: Select your `healthcare-voice-assistant` repo.
    *   **Branch**: Select `main`.
    *   **Deployment settings**: Select "Automatic" (so it updates when you push code).
    *   Click **Next**.
4.  **Configure Build**:
    *   **Configuration file**: Select "Configure all settings here".
    *   **Runtime**: Select `Python 3.10`.
    *   **Build command**: `pip install -r requirements.txt`
    *   **Start command**: `python main.py`
    *   **Port**: `8765` (Important! Change default 8080 to 8765).
    *   Click **Next**.
5.  **Configure Service**:
    *   **Service name**: Enter `healthcare-backend`.
    *   **Environment variables** (Click "Add environment variable"):
        *   Key: `DEEPGRAM_API_KEY` | Value: `your_key_here`
        *   Key: `OPENAI_API_KEY`   | Value: `your_key_here`
        *   Key: `ELEVENLABS_API_KEY`| Value: `your_key_here`
    *   *(Optional)* **Auto scaling**: Leave defaults.
    *   *(Optional)* **Health check**: Leave defaults.
    *   Click **Next**, then **Create & Deploy**.
6.  **Wait**: It will take 5-10 minutes.
7.  **Copy URL**: Once active, copy the "Default domain" (e.g., `https://xyz.awsapprunner.com`). 
    *   **Note**: We need the **WSS** version. Just replace `https://` with `wss://`.
    *   Example: `wss://xyz.awsapprunner.com` -> **SAVE THIS URL!**

### (Alternative) Part 1: Deploy from ECR Image
*If you already have a Docker image in Amazon ECR:*

1.  **Source**: Select "Container registry".
2.  **Provider**: Select "Amazon ECR".
3.  **Image URI**: Browse and select your image tag (e.g., `latest`).
4.  **Deployment settings**: "Automatic" (if you want auto-deploy on new images) or "Manual".
5.  **Configuration**:
    *   **Port**: `8765`
    *   **Start command**: Leave empty (it uses the Dockerfile's CMD).
    *   **Environment variables**: Same as above (Add your 3 API keys).
    *   Proceed to deploy.

---

## Part 2: Deploy Frontend (AWS Amplify)
*This hosts the "Website" (UI) that you see in the browser.*

1.  **Go to AWS Amplify**: Search for "Amplify" in AWS.
2.  **Click "Create new app"** -> "GitHub".
3.  **Connect Repo**:
    *   Select your `healthcare-voice-assistant` repo and `main` branch.
    *   Click **Next**.
4.  **Build Settings** (The detailed part):
    *   **App name**: `healthcare-frontend`.
    *   **Frontend build command**: Leave blank (or type `echo "Skip"`).
    *   **Build output directory**: Type `client`.
    *   **IMPORTANT**: Click the **"Edit YML file"** button.
    *   **Replace everything** with this code:
        ```yaml
        version: 1
        frontend:
          phases:
            build:
              commands:
                - sed -i "s|__WEBSOCKET_URL__|$WEBSOCKET_URL|g" client/index.html
          artifacts:
            baseDirectory: client
            files:
              - '**/*'
        ```
    *   Click **Save** inside the editor.
    *   Click **Next**.
5.  **Review & Create**:
    *   Click **Save and deploy**.
6.  **Configure Environment Variable** (Connect the Frontend to Backend):
    *   **WAIT** for the first deployment (it might fail or simple work but point to localhost).
    *   Go to **App settings** (left menu) -> **Environment variables**.
    *   Click **Manage variables**.
    *   Add a variable:
        *   **Key**: `WEBSOCKET_URL`
        *   **Value**: Paste the **WSS URL** from Part 1 (e.g., `wss://xyz.awsapprunner.com`).
    *   Click **Save**.
7.  **Re-deploy**:
    *   Go back to the main app page.
    *   Click **"Redeploy this version"**.
    *   *Reason*: The environment variable only takes effect during the build process, so we need to run the build again.

---

## ✅ Setup Complete!
Open the **Amplify Domain** (e.g., `https://main.xyz.amplifyapp.com`).
Your Voice Assistant is now live and talking to your cloud backend! 🎤☁️
