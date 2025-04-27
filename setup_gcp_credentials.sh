#!/bin/bash
# setup_gcp_credentials.sh - Script to set up Google Cloud Application Default Credentials

# Text styling
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Banner
echo -e "${BOLD}${BLUE}"
echo "=========================================================="
echo "   Google Cloud Application Default Credentials Setup"
echo "=========================================================="
echo -e "${NC}"

# Step 1: Check if gcloud is installed
echo -e "${BOLD}Step 1: Checking if gcloud CLI is installed...${NC}"
if command_exists gcloud; then
    echo -e "  ${GREEN}✓ gcloud CLI is installed${NC}"
else
    echo -e "  ${RED}✗ gcloud CLI is not installed${NC}"
    echo -e "${YELLOW}Please install the Google Cloud SDK first:${NC}"
    echo "  - macOS: brew install --cask google-cloud-sdk"
    echo "  - Manual download: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Step 2: Check gcloud configuration
echo -e "\n${BOLD}Step 2: Checking gcloud configuration...${NC}"
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null)

if [[ -z "$CURRENT_PROJECT" || "$CURRENT_PROJECT" == "(unset)" ]]; then
    echo -e "  ${YELLOW}⚠ No default project is configured${NC}"
    echo "  You should consider setting a default project:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
else
    echo -e "  ${GREEN}✓ Current project: $CURRENT_PROJECT${NC}"
fi

if [[ -z "$CURRENT_ACCOUNT" || "$CURRENT_ACCOUNT" == "(unset)" ]]; then
    echo -e "  ${YELLOW}⚠ No default account is configured${NC}"
    echo "  You will need to authenticate in the next step."
else
    echo -e "  ${GREEN}✓ Current account: $CURRENT_ACCOUNT${NC}"
fi

# Step 3: Check for existing ADC
echo -e "\n${BOLD}Step 3: Checking for existing Application Default Credentials...${NC}"

# Determine ADC path based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows
    ADC_PATH="$APPDATA/gcloud/application_default_credentials.json"
else
    ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"
fi

if [[ -f "$ADC_PATH" ]]; then
    echo -e "  ${GREEN}✓ Application Default Credentials already exist at:${NC}"
    echo "    $ADC_PATH"
    
    read -p "  Do you want to refresh these credentials? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "  ${GREEN}Keeping existing credentials.${NC}"
        echo -e "\n${BOLD}${GREEN}ADC Setup Complete!${NC} Your code should now be able to use these credentials."
        echo -e "To use these credentials, make sure your code can access them with:"
        echo -e "  export GOOGLE_APPLICATION_CREDENTIALS=\"$ADC_PATH\""
        exit 0
    fi
else
    echo -e "  ${YELLOW}⚠ No Application Default Credentials found${NC}"
fi

# Step 4: Run gcloud auth application-default login
echo -e "\n${BOLD}Step 4: Setting up Application Default Credentials...${NC}"
echo "  This will open a browser window for you to log in with your Google account."
echo "  Please make sure this account has the necessary permissions for your project."
echo -e "  ${YELLOW}Press Enter to continue or Ctrl+C to cancel...${NC}"
read

gcloud auth application-default login

# Step 5: Verify credentials were created
echo -e "\n${BOLD}Step 5: Verifying credentials...${NC}"
if [[ -f "$ADC_PATH" ]]; then
    echo -e "  ${GREEN}✓ Application Default Credentials successfully created at:${NC}"
    echo "    $ADC_PATH"
    
    # Extract some information from the credentials
    if command_exists jq; then
        CLIENT_ID=$(jq -r '.client_id' "$ADC_PATH" 2>/dev/null)
        if [[ $? -eq 0 && -n "$CLIENT_ID" ]]; then
            echo -e "  ${GREEN}✓ Credentials look valid (client_id: ${CLIENT_ID:0:15}...)${NC}"
        fi
    fi
else
    echo -e "  ${RED}✗ Failed to create Application Default Credentials${NC}"
    echo "  Please check for errors in the output above."
    exit 1
fi

# Final instructions
echo -e "\n${BOLD}${GREEN}ADC Setup Complete!${NC}"
echo -e "Your code should now be able to use these credentials automatically."
echo -e "If your code requires an explicit path, use:"
echo -e "${BOLD}export GOOGLE_APPLICATION_CREDENTIALS=\"$ADC_PATH\"${NC}"
echo
echo -e "To verify these credentials work with your GCP project, try running:"
echo -e "${BOLD}python -c 'from google.cloud import storage; print(\"Credentials working!\") if storage.Client() else print(\"Failed\")'${NC}"
echo
echo -e "To revoke these credentials later, use:"
echo -e "${BOLD}gcloud auth application-default revoke${NC}" 