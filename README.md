# ProteinDJ - Cloud-Deployable Fork

**Cloud-ready protein design pipeline with custom AI loss functions for RunPod/GPU cloud deployment**

[![Original ProteinDJ](https://img.shields.io/badge/Original-ProteinDJ-blue)](https://github.com/PapenfussLab/proteindj)
[![Publication](https://img.shields.io/badge/DOI-10.1002/pro.70464-green)](https://onlinelibrary.wiley.com/doi/10.1002/pro.70464)
[![License](https://img.shields.io/badge/License-Academic-orange)](LICENSE)

---

## About This Fork

This is a modified version of [ProteinDJ](https://github.com/PapenfussLab/proteindj) optimized for cloud GPU deployment (RunPod, vast.ai, etc.) with:

- 🐳 **Docker containerization** for one-click deployment
- 🔬 **Custom AI loss functions** (pH-sensitive Histidine logic, multi-state design)
- ☁️ **Cloud-native architecture** with live code editing
- 🔐 **SSH access** and port forwarding for remote monitoring
- 📊 **Automated setup** via GitHub integration

## Original ProteinDJ

**ProteinDJ** is a Nextflow pipeline for protein design developed by the Papenfuss Lab.

### Key Features
- **RFdiffusion** - Generative protein design
- **ProteinMPNN** - Sequence design
- **AlphaFold2** - Structure prediction
- **PyRosetta** - Analysis and filtering
- Multiple design modes (monomer, binder, fold-conditioning, etc.)

### Original Authors & Contributors
- **Dylan Silke** - Pipeline architecture and development
- **Joshua Hardy** - Development and testing
- **Julie Iskander** - Development
- **Anthony Papenfuss** - Principal Investigator
- **Lyn Deng** - Logo design

**Citation:**
> Silke, D., Iskander, J., Pan, J., Thompson, A.P., Papenfuss, A.T., Lucet, I.S., Hardy, J.M. (2026).
> *ProteinDJ: a high-performance and modular protein design pipeline.*
> Protein Science. [DOI: 10.1002/pro.70464](https://onlinelibrary.wiley.com/doi/10.1002/pro.70464)

---

## Modifications in This Fork

### 1. Cloud Deployment Infrastructure

**Added by:** Luke (2026)

- `Dockerfile.runpod` - RunPod-optimized container
- `post_start.sh` - Automatic configuration on startup
- `build_and_deploy.sh` - One-command deployment script
- SSH server configuration with port forwarding

### 2. Custom AI Loss Functions

**Added by:** Luke (2026)

Located in `custom_logic/`:

- **pH-Sensitive Histidine Loss** - Penalizes histidines at interfaces based on Henderson-Hasselbalch equation
- **Multi-State Design Loss** - Optimizes proteins that bind multiple targets
- **Interface Energy Loss** - Improves H-bonds, hydrophobic packing, electrostatics
- Integration framework for AlphaFold2 pipeline

**Scientific Rationale:**
Histidine (pKa ~6.0) is partially protonated at physiological pH, causing pH-dependent binding affinity changes. Our custom loss function addresses this by penalizing interface histidines unless functionally required.

---

## Custom Loss Functions

### pH-Sensitive Histidine Loss

Penalizes histidines based on:
- Protonation state at target pH (Henderson-Hasselbalch)
- Surface accessibility (SASA)
- Interface proximity

**Configuration:**
```json
{
  "use_ph_sensitive": true,
  "ph_value": 7.4,
  "custom_loss_weight": 0.3
}
```

### Multi-State Design

Optimizes sequences that work across multiple binding states while maintaining consistency.

### Interface Energy

Encourages favorable contacts:
- Hydrogen bonds
- Hydrophobic packing
- Electrostatic complementarity
- Clash avoidance

**See [custom_logic/README.md](custom_logic/README.md) for scientific details.**

---

## Software Credits

This pipeline integrates multiple external packages:

### Core Tools
- **AlphaFold2** - Jumper et al. (2021) - Structure prediction
- **RFdiffusion** - Watson et al. (2023) - Generative design
- **ProteinMPNN** - Dauparas et al. (2022) - Sequence design
- **PyRosetta** - Chaudhury et al. (2010) - Analysis

### Additional Tools
- **BindCraft** - Pacesa et al. (2025) - One-shot binder design
- **Boltz-2** - Wohlwend et al. (2024) - Biomolecular interaction modeling
- **Full-Atom MPNN** - Shuai et al. (2025) - Sidechain design
- **HyperMPNN** - Ertelt et al. (2024) - Thermostable protein design
- **BioPython** - Cock et al. (2009) - Computational biology tools

---

## License & Usage

### ProteinDJ Pipeline
- **License:** Academic use (see [LICENSE](LICENSE))
- **PyRosetta:** Requires license for commercial projects
- **Citation Required:** Please cite the original ProteinDJ publication

---


## Acknowledgments

### Original ProteinDJ Development
- **Papenfuss Lab** - Walter and Eliza Hall Institute
- **Lucet Lab** - Walter and Eliza Hall Institute
- All contributors to the external tools integrated in ProteinDJ

### Cloud Deployment Modifications
- Built on the excellent foundation provided by the ProteinDJ team
- Inspired by the need for accessible cloud-based protein design
- Developed for democratizing access to GPU-accelerated protein engineering


**Original Repository:** https://github.com/PapenfussLab/proteindj
**Publication:** https://onlinelibrary.wiley.com/doi/10.1002/pro.70464