# Google Cloud Setup for Text-to-Speech Long Audio API

This guide walks through setting up Google Cloud Platform for use with the Text-to-Speech Long Audio API in the minibook_composer project.

## Automatic Setup Script

For your convenience, this project includes an automated setup script that handles the core authentication process:

```bash
./setup_gcp_credentials.sh
```

**What the script handles:**
- Checking if gcloud CLI is installed
- Verifying your gcloud configuration
- Setting up Application Default Credentials (ADC)
- Displaying the credentials path to use with your environment

**What you'll need to do manually (covered in this guide):**
- Installing gcloud CLI (if not already installed)
- Enabling the required APIs
- Setting up the storage bucket
- Installing ffmpeg for WAV to MP3 conversion
- Setting project-specific configuration values

## Prerequisites

- A Google account with access to Google Cloud Platform
- The project depends on these packages:
  - `google-cloud-texttospeech`
  - `google-cloud-storage`
  - `pydub` (for audio conversion)
  - `ffmpeg` (for audio format conversion)

## Setting Up Google Cloud CLI

1. **Install the Google Cloud CLI**

   ```bash
   # macOS (using Homebrew)
   brew install --cask google-cloud-sdk
   
   # Windows
   # Download from https://cloud.google.com/sdk/docs/install-sdk#windows
   
   # Linux
   echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
   sudo apt-get update && sudo apt-get install google-cloud-sdk
   ```

2. **Log in to Google Cloud**

   ```bash
   gcloud auth login
   ```

## Setting Up Application Default Credentials (ADC)

**Note:** This step is automated by `setup_gcp_credentials.sh` but included here for manual setup.

1. **Set up Application Default Credentials**

   This creates the credentials file your application will use:

   ```bash
   gcloud auth application-default login
   ```

   This will:
   - Open a browser window asking you to log in with your Google account
   - Create a credentials file at `~/.config/gcloud/application_default_credentials.json`

2. **Set the default project**

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Update the quota project in ADC**

   ```bash
   gcloud auth application-default set-quota-project YOUR_PROJECT_ID
   ```

## Enabling Required APIs

This step must be done manually:

```bash
gcloud services enable texttospeech.googleapis.com storage.googleapis.com
```

## Setting Up Storage Bucket

The Long Audio API requires a Google Cloud Storage bucket to store the generated audio files.

1. **Create a bucket (if not already exist)**

   ```bash
   gsutil mb -p YOUR_PROJECT_ID gs://YOUR_BUCKET_NAME
   ```

2. **Verify the bucket exists**

   ```bash
   gsutil ls gs://YOUR_BUCKET_NAME
   ```

## Installing ffmpeg (for MP3 conversion)

The Long Audio API only outputs WAV files. To convert them to MP3, install ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Environment Variables (if needed)

If your code requires an explicit path to the credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="~/.config/gcloud/application_default_credentials.json"
```

## Testing the Setup

Verify your credentials are working:

```bash
python -c 'from google.cloud import storage; print("Credentials working!") if storage.Client() else print("Failed")'
```

## Important Notes

1. **Long Audio API Limitations**:
   - Only supports LINEAR16 (WAV) format, not MP3 or OGG directly
   - Text input limit is 100,000 characters
   - Processing takes longer than standard API

2. **Project Configuration**:
   - Update your project's configuration file with:
     - Your Project ID
     - Your GCS Bucket name

3. **Credentials Location**:
   - macOS/Linux: `~/.config/gcloud/application_default_credentials.json`
   - Windows: `%APPDATA%\gcloud\application_default_credentials.json`

4. **Authentication Warning**:
   If you see a warning like: "Your application has authenticated using end user credentials from Google Cloud SDK without a quota project", run:
   ```bash
   gcloud auth application-default set-quota-project YOUR_PROJECT_ID
   ```

## Revoking Credentials

When you no longer need the credentials or want to switch accounts:

```bash
# Revoke application default credentials
gcloud auth application-default revoke

# Revoke all credentials
gcloud auth revoke --all
```

## Troubleshooting

1. **API not enabled errors**:
   Check that the required APIs are enabled in the Google Cloud Console:
   - Text-to-Speech API
   - Cloud Storage API

2. **Permission denied errors**:
   Ensure your Google account has the necessary permissions:
   - Text-to-Speech Admin
   - Storage Admin

3. **Audio conversion errors**:
   If you see: "Couldn't find ffmpeg or avconv", install ffmpeg:
   ```bash
   brew install ffmpeg  # for macOS
   ```

## References

- [Google Cloud Text-to-Speech Documentation](https://cloud.google.com/text-to-speech/docs)
- [Long Audio Synthesis Guide](https://cloud.google.com/text-to-speech/docs/create-audio-text-long-audio-synthesis)
- [Application Default Credentials Guide](https://cloud.google.com/docs/authentication/application-default-credentials) 