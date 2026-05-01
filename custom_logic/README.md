# ProteinDJ Custom Loss Functions

Custom AI loss functions for protein design with pH-sensitive Histidine logic and multi-state design capabilities.

## Overview

This module extends the AlphaFold2 loss functions used in ProteinDJ with domain-specific constraints:

1. **pH-Sensitive Histidine Loss**: Penalizes histidines in problematic positions based on target pH
2. **Multi-State Design Loss**: Enables design of proteins that bind multiple targets
3. **Interface Energy Loss**: Optimizes protein-protein interface quality

## Files

- `loss.py`: Main loss function implementations
- `integrate_losses.py`: Integration module for ProteinDJ pipeline
- `loss_config.json`: Configuration parameters
- `README.md`: This file

## Quick Start

### 1. Test the Loss Module

```bash
python loss.py
```

### 2. Test Integration

```bash
python integrate_losses.py --test
```

### 3. Use in ProteinDJ Pipeline

```python
from integrate_losses import setup_proteindj_custom_losses

# At the start of your pipeline
setup_proteindj_custom_losses('loss_config.json')
```

## pH-Sensitive Histidine Loss

### Motivation

Histidine (His, H) is unique among amino acids due to its pKa ~6.0, making it the only amino acid with a side chain that can be protonated/deprotonated near physiological pH. This property makes histidines:

- **Problematic for stability**: pH changes alter binding affinity
- **Difficult to predict**: Protonation state affects structure
- **Experimentally challenging**: Results vary with buffer pH

### Implementation

The loss function uses the Henderson-Hasselbalch equation:

```
pH = pKa + log([A-]/[HA])
```

To calculate protonation fraction at target pH:

```
f_protonated = 1 / (1 + 10^(pH - pKa))
```

**Penalty Strategy**:
- Base penalty for all histidines
- Increased penalty for surface-exposed histidines (SASA > 25%)
- Maximum penalty for interface histidines (2x boost)
- Scaled by pH sensitivity (maximum at pH 6.0)

### Configuration

```json
{
  "ph_value": 7.0,              // Target pH (physiological = 7.4)
  "penalty_weight": 1.0,         // Base penalty weight
  "interface_boost": 2.0         // Multiplier for interface histidines
}
```

### Example

```python
from loss import pHSensitiveHistidineLoss

# Create loss function for pH 7.4 (physiological)
loss_fn = pHSensitiveHistidineLoss(ph_value=7.4)

# Calculate loss
loss = loss_fn(
    sequence=sequence_tensor,       # (B, L, 20)
    structure=structure_tensor,     # (B, L, 3)
    interface_mask=interface_mask,  # (B, L)
    sasa=sasa_tensor               # (B, L)
)
```

## Multi-State Design Loss

### Motivation

Many proteins must bind multiple targets or exist in multiple conformations. Traditional design optimizes for a single state, but multi-state design ensures:

- Binding to multiple targets
- Conformational flexibility
- Allosteric regulation

### Implementation

The loss ensures:
1. Each state meets quality thresholds (RMSD, pLDDT)
2. Sequence consistency across states
3. Weighted importance of different states

### Configuration

```json
{
  "num_states": 2,
  "state_weights": [1.0, 0.8],     // Relative importance
  "consistency_weight": 0.5         // Sequence consistency penalty
}
```

### Example

```python
from loss import MultiStateDesignLoss

loss_fn = MultiStateDesignLoss(
    num_states=2,
    state_weights=[1.0, 0.8]
)

# Calculate loss
loss, metrics = loss_fn(
    predictions=[state1_pred, state2_pred],
    targets=[state1_target, state2_target]
)
```

## Interface Energy Loss

### Motivation

Protein-protein interfaces must have favorable energetics:
- Hydrogen bonds for specificity
- Hydrophobic packing for affinity
- Electrostatic complementarity
- No steric clashes

### Implementation

Calculates approximate energy components:
- H-bond potential (donors/acceptors, geometry)
- Hydrophobic packing (buried surface area)
- Electrostatic interactions (charge complementarity)
- Clash penalty (atoms too close)

### Configuration

```json
{
  "hbond_weight": 1.0,
  "hydrophobic_weight": 0.8,
  "electrostatic_weight": 1.2,
  "clash_penalty": 10.0
}
```

## Combined Loss

The `CombinedProteinDesignLoss` integrates all losses:

```python
from loss import CombinedProteinDesignLoss

loss_fn = CombinedProteinDesignLoss(
    use_ph_sensitive=True,
    use_multistate=False,
    use_interface_energy=True,
    ph_value=7.4
)

# Calculate combined loss
total_loss, metrics = loss_fn(
    predictions={'sequence': seq, 'structure': struct},
    interface_mask=interface_mask,
    sasa=sasa
)

print(f"Total Loss: {total_loss.item()}")
print(f"Metrics: {metrics}")
```

## Integration with AlphaFold2

The custom losses are combined with AlphaFold2's default loss:

```python
combined_loss = (1 - α) * af2_loss + α * custom_loss
```

Where `α` is the `custom_loss_weight` parameter (default: 0.3).

## Scientific Background

### Histidine pKa Values

| Context | pKa Range | Notes |
|---------|-----------|-------|
| Free amino acid | 6.0 | Standard value |
| Buried in protein | 6.5-7.5 | Shifted by environment |
| At interface | 5.5-6.5 | Often shifted |
| In active sites | 4.0-8.0 | Wide variation |

### pH Ranges of Interest

| Environment | pH | Use Case |
|-------------|-----|----------|
| Gastric | 1.5-3.5 | Oral drugs |
| Lysosomal | 4.5-5.0 | Endosomal escape |
| Physiological | 7.35-7.45 | Most proteins |
| Alkaline | 8.0-9.0 | Some enzymes |

### Design Principles

1. **Minimize histidines at interfaces** (unless functionally required)
2. **Replace His with Asn/Gln** for H-bond donors without pH sensitivity
3. **Use His intentionally** for pH-responsive switches
4. **Test at multiple pH values** to ensure robust binding

## Advanced Usage

### Custom Amino Acid Indexing

If your amino acid encoding differs from standard:

```python
loss_fn = pHSensitiveHistidineLoss(...)
loss_fn.HIS_IDX = 7  # Adjust to your encoding
```

### Per-Residue Penalties

```python
# Get per-residue penalties instead of sum
his_mask = sequence[:, :, HIS_IDX] > 0.5
interface_his_penalty = (his_mask & interface_mask).float() * 2.0
```

### Logging and Debugging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now loss functions will log detailed information
```

## Citation

If you use these custom loss functions in your research, please cite:

```bibtex
@software{proteindj_custom_losses,
  author = {Luke},
  title = {Custom Loss Functions for ProteinDJ},
  year = {2026},
  url = {https://github.com/yourusername/proteindj-custom-logic}
}
```

And the original ProteinDJ paper:

```bibtex
@article{silke2026proteindj,
  title={ProteinDJ: a high-performance and modular protein design pipeline},
  author={Silke, Dylan and others},
  journal={Protein Science},
  year={2026},
  doi={10.1002/pro.70464}
}
```

## Contributing

To contribute improvements:

1. Fork this repository
2. Make your changes
3. Add tests
4. Submit a pull request

## Support

For questions or issues:
- Open an issue on GitHub
- Contact: luke@example.com

## License

MIT License - see LICENSE file for details
