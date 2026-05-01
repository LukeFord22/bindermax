#!/bin/bash
# RunPod Post-Start Script for bindermax
# This script runs automatically when the container launches
# It assumes the entire bindermax repo (with custom logic) is already cloned
# by the entrypoint script at /workspace/bindermax

set -e

echo "=========================================="
echo "bindermax Post-Start Configuration"
echo "=========================================="

# Environment variables
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
BINDERMAX_DIR="${BINDERMAX_DIR:-/workspace/bindermax}"
CUSTOM_LOGIC_DIR="${BINDERMAX_DIR}/custom_logic"
AUTO_DOWNLOAD_MODELS="${AUTO_DOWNLOAD_MODELS:-false}"

# Verify we're in the right place
if [ ! -d "$BINDERMAX_DIR" ] || [ ! -f "$BINDERMAX_DIR/main.nf" ]; then
    echo " Error: bindermax not found at $BINDERMAX_DIR"
    echo "   This script expects bindermax to be cloned by the entrypoint"
    exit 1
fi

cd "$BINDERMAX_DIR"

echo ""
echo "✓ bindermax repository: $BINDERMAX_DIR"

# [1/4] Set up Python environment
echo ""
echo "[1/4] Configuring Python Environment..."

# Add custom logic to PYTHONPATH
export PYTHONPATH="$CUSTOM_LOGIC_DIR:$PYTHONPATH"
echo "export PYTHONPATH=\"$CUSTOM_LOGIC_DIR:\$PYTHONPATH\"" >> ~/.bashrc

# Install custom Python dependencies if requirements.txt exists
if [ -f "$CUSTOM_LOGIC_DIR/requirements.txt" ]; then
    echo "Installing custom Python dependencies..."
    pip install -q -r "$CUSTOM_LOGIC_DIR/requirements.txt"
    echo " Dependencies installed"
else
    echo "  No custom requirements.txt found"
fi

# [2/4] Download models if requested
echo ""
echo "[2/4] Checking Model Downloads..."

MODEL_MARKER="/workspace/models/.models_downloaded"

if [ -f "$MODEL_MARKER" ]; then
    echo "✓ Models already downloaded (marker file exists)"
elif [ "$AUTO_DOWNLOAD_MODELS" == "true" ]; then
    echo "Downloading models (~11GB, takes 10-20 minutes)..."
    if [ -f "$BINDERMAX_DIR/scripts/download_models.sh" ]; then
        bash "$BINDERMAX_DIR/scripts/download_models.sh"
        # Create marker file
        mkdir -p /workspace/models
        touch "$MODEL_MARKER"
        echo "✓ Models downloaded successfully"
    else
        echo "  download_models.sh not found"
    fi
else
    echo "  Automatic model download disabled"
    echo "   Set AUTO_DOWNLOAD_MODELS=true to enable"
    echo "   Or manually run: bash scripts/download_models.sh"
fi

# [3/4] Set up Nextflow monitoring
echo ""
echo "[3/4] Setting Up Nextflow Monitoring..."

# Create Nextflow config for web monitoring
cat > "$WORKSPACE_DIR/nextflow_monitoring.config" << 'EOF'
// Nextflow Web Monitoring Configuration
// Access via SSH port forwarding: ssh -L 8080:localhost:8080 root@<runpod-ip>

weblog {
    enabled = true
    url = 'http://0.0.0.0:8080'
}

timeline {
    enabled = true
    file = 'timeline.html'
}

report {
    enabled = true
    file = 'report.html'
}

dag {
    enabled = true
    file = 'dag.html'
}
EOF

echo "✓ Nextflow monitoring configured on port 8080"

# [4/4] Create helper scripts
echo ""
echo "[4/4] Creating Helper Scripts..."

# SSH tunnel instructions
cat > "$WORKSPACE_DIR/ssh_tunnel_instructions.txt" << 'EOF'
========================================
SSH Port Forwarding Instructions
========================================

To access Nextflow monitoring locally:

1. From your local machine, create SSH tunnel:

   ssh -L 8080:localhost:8080 -p <RUNPOD_SSH_PORT> root@<RUNPOD_IP>

2. Open in your browser:

   http://localhost:8080

3. To run tunnel in background:

   ssh -fN -L 8080:localhost:8080 -p <RUNPOD_SSH_PORT> root@<RUNPOD_IP>

Replace <RUNPOD_SSH_PORT> and <RUNPOD_IP> with your pod's details
(found in RunPod console)

========================================
EOF

# Quick run script
cat > "$WORKSPACE_DIR/run_pipeline.sh" << 'EOF'
#!/bin/bash
# Quick pipeline runner

cd /workspace/bindermax

if [ $# -eq 0 ]; then
    echo "Usage: ./run_pipeline.sh <profile> [additional nextflow args]"
    echo ""
    echo "Available profiles:"
    echo "  - monomer_denovo"
    echo "  - binder_denovo"
    echo "  - binder_foldcond"
    echo ""
    echo "Example: ./run_pipeline.sh binder_denovo"
    exit 1
fi

PROFILE=$1
shift

echo "Starting bindermax pipeline with profile: $PROFILE"
nextflow run main.nf -profile "$PROFILE" "$@"
EOF
chmod +x "$WORKSPACE_DIR/run_pipeline.sh"

echo "✓ Helper scripts created"

# Display final status
echo ""
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo ""
echo "Directories:"
echo "   Workspace:     $WORKSPACE_DIR"
echo "   bindermax:     $BINDERMAX_DIR"
echo "   Custom Logic:  $CUSTOM_LOGIC_DIR"
echo "   Models:        /workspace/models"
echo "   Runs:          /workspace/runs"
echo ""
echo "Quick Start:"
echo "   1. View SSH tunnel instructions: cat /workspace/ssh_tunnel_instructions.txt"
echo "   2. Run pipeline: /workspace/run_pipeline.sh binder_denovo"
echo ""
echo "Next Steps:"

if [ "$AUTO_DOWNLOAD_MODELS" != "true" ] && [ ! -f "$MODEL_MARKER" ]; then
    echo "   Download models first: cd $BINDERMAX_DIR && bash scripts/download_models.sh"
fi

echo "   - Edit custom losses: nano $CUSTOM_LOGIC_DIR/loss_config.json"
echo "   - Configure pipeline: nano $BINDERMAX_DIR/nextflow.config"
echo "   - Test custom losses: python $CUSTOM_LOGIC_DIR/integrate_losses.py --test"
echo ""
echo "Documentation:"
echo "   - Setup Guide: cat $BINDERMAX_DIR/SETUP_GUIDE.md"
echo "   - Full Docs: cat $BINDERMAX_DIR/RUNPOD_DEPLOYMENT.md"
echo ""
echo "=========================================="

exit 0
