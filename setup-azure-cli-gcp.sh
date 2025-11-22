#!/bin/bash
# Azure CLI Setup for GCP VM - for Azure Container Registry Access
# Run this script on your GCP VM to enable ACR access

set -e

echo "☁️ Setting up Azure CLI for Azure Container Registry access..."

# Check if Azure CLI is installed
if command -v az &> /dev/null; then
    echo "✅ Azure CLI is already installed"
    az --version
else
    echo "📥 Installing Azure CLI..."
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    echo "✅ Azure CLI installed successfully"
fi

# Create Azure CLI configuration directory
mkdir -p ~/.azure

echo ""
echo "🔐 Azure Container Registry Authentication Setup"
echo "=============================================="
echo ""
echo "📋 You have two options for ACR authentication:"
echo ""
echo "1. 🔑 Service Principal (Recommended for automation)"
echo "   - Create a service principal in Azure"
echo "   - Grant AcrPull permissions to your ACR"
echo "   - Use client ID and secret for authentication"
echo ""
echo "2. 👤 User Account (For manual testing)"
echo "   - Use 'az login' for interactive authentication"
echo "   - Good for testing and development"
echo ""
echo "🚀 For Azure DevOps Pipeline:"
echo "The pipeline will handle authentication automatically using the"
echo "service connection you configured in Azure DevOps."
echo ""

# Function to test ACR access
test_acr_access() {
    local acr_name="$1"
    echo "🧪 Testing ACR access..."
    
    if az acr login --name "$acr_name" &>/dev/null; then
        echo "✅ Successfully authenticated with ACR: $acr_name"
        
        # Test docker pull capabilities
        echo "🐳 Testing Docker pull capabilities..."
        if docker pull mcr.microsoft.com/hello-world:latest &>/dev/null; then
            echo "✅ Docker pull test successful"
            docker rmi mcr.microsoft.com/hello-world:latest &>/dev/null || true
        else
            echo "⚠️ Docker pull test failed - check Docker installation"
        fi
    else
        echo "❌ Failed to authenticate with ACR: $acr_name"
        echo "💡 Make sure you're logged into Azure: az login"
    fi
}

# Interactive setup
echo "🔧 Would you like to set up authentication now? (y/n)"
read -r setup_auth

if [[ "$setup_auth" =~ ^[Yy]$ ]]; then
    echo ""
    echo "📝 Enter your Azure Container Registry name (e.g., shifthandoverregistry):"
    read -r acr_name
    
    if [[ -n "$acr_name" ]]; then
        echo ""
        echo "🔑 Choose authentication method:"
        echo "1. Interactive login (az login)"
        echo "2. Service principal (requires client ID and secret)"
        echo "Enter choice (1 or 2):"
        read -r auth_choice
        
        case "$auth_choice" in
            1)
                echo "🌐 Starting interactive Azure login..."
                az login
                test_acr_access "$acr_name"
                ;;
            2)
                echo "📝 Enter Service Principal Client ID:"
                read -r client_id
                echo "🔐 Enter Service Principal Client Secret:"
                read -rs client_secret
                echo "📝 Enter Tenant ID:"
                read -r tenant_id
                
                if az login --service-principal --username "$client_id" --password "$client_secret" --tenant "$tenant_id"; then
                    echo "✅ Service principal authentication successful"
                    test_acr_access "$acr_name"
                else
                    echo "❌ Service principal authentication failed"
                fi
                ;;
            *)
                echo "❌ Invalid choice. Skipping authentication setup."
                ;;
        esac
    else
        echo "❌ No ACR name provided. Skipping authentication test."
    fi
else
    echo "⏭️ Skipping authentication setup."
fi

echo ""
echo "📋 Useful Azure CLI Commands:"
echo "=============================="
echo ""
echo "# Login to Azure"
echo "az login"
echo ""
echo "# Login to specific ACR"
echo "az acr login --name your-acr-name"
echo ""
echo "# List ACR repositories"
echo "az acr repository list --name your-acr-name"
echo ""
echo "# List image tags"
echo "az acr repository show-tags --name your-acr-name --repository shift-handover-app"
echo ""
echo "# Pull image from ACR"
echo "docker pull your-acr-name.azurecr.io/shift-handover-app:latest"
echo ""

echo "✅ Azure CLI setup completed!"
echo ""
echo "💡 Next Steps:"
echo "1. Configure Azure DevOps service connection for ACR"
echo "2. Update pipeline variable groups with ACR details"
echo "3. Run your Azure DevOps pipeline"
echo ""
echo "🔍 The pipeline will automatically handle ACR authentication"
echo "   and deploy your application to this GCP VM."