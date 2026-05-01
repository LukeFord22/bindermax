"""
Custom Loss Functions for ProteinDJ
Author: Luke
Description: pH-sensitive Histidine logic and Multi-state design for protein binders
License: MIT

This module provides custom loss functions that extend AlphaFold2's capabilities
with domain-specific constraints for protein design.

Key Features:
1. pH-Sensitive Histidine Penalization
2. Multi-state Design Loss
3. Interface Energy Optimization
4. Structural Stability Metrics
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Optional, Tuple, List


class pHSensitiveHistidineLoss(nn.Module):
    """
    Loss function for pH-sensitive histidine residues.

    Histidine has a pKa ~6.0, making it particularly sensitive to pH changes.
    This loss penalizes histidines in surface-exposed or interface positions
    where pH sensitivity would affect binding.

    Args:
        ph_value (float): Target pH for design (default: 7.0)
        penalty_weight (float): Weight for histidine penalty (default: 1.0)
        interface_boost (float): Additional penalty for interface histidines (default: 2.0)
    """

    def __init__(
        self,
        ph_value: float = 7.0,
        penalty_weight: float = 1.0,
        interface_boost: float = 2.0
    ):
        super().__init__()
        self.ph_value = ph_value
        self.penalty_weight = penalty_weight
        self.interface_boost = interface_boost

        # Calculate protonation state at target pH
        # Henderson-Hasselbalch: pH = pKa + log([A-]/[HA])
        self.his_pka = 6.0
        self.protonation_fraction = self._calculate_protonation()

    def _calculate_protonation(self) -> float:
        """Calculate fraction of protonated histidine at target pH."""
        return 1.0 / (1.0 + 10 ** (self.ph_value - self.his_pka))

    def forward(
        self,
        sequence: torch.Tensor,
        structure: torch.Tensor,
        interface_mask: Optional[torch.Tensor] = None,
        sasa: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Calculate pH-sensitive histidine loss.

        Args:
            sequence: One-hot encoded sequence (B, L, 20)
            structure: Predicted structure coordinates (B, L, 3)
            interface_mask: Binary mask for interface residues (B, L)
            sasa: Solvent accessible surface area (B, L)

        Returns:
            loss: Scalar loss value
        """
        batch_size, seq_len, _ = sequence.shape

        # Histidine index in standard amino acid ordering
        HIS_IDX = 8  # Adjust based on your encoding

        # Identify histidine positions
        his_mask = sequence[:, :, HIS_IDX] > 0.5  # (B, L)

        if not his_mask.any():
            return torch.tensor(0.0, device=sequence.device)

        # Calculate base penalty for all histidines
        his_penalty = his_mask.float().sum()

        # Increase penalty for surface-exposed histidines
        if sasa is not None:
            surface_threshold = 0.25  # 25% SASA threshold
            surface_his = his_mask & (sasa > surface_threshold)
            his_penalty += surface_his.float().sum() * 0.5

        # Strongly penalize interface histidines (most problematic)
        if interface_mask is not None:
            interface_his = his_mask & interface_mask
            his_penalty += interface_his.float().sum() * self.interface_boost

        # Scale by protonation fraction (more penalty when partially protonated)
        # Maximum penalty at pH ~6.0 where 50% protonated
        ph_sensitivity = 2.0 * self.protonation_fraction * (1.0 - self.protonation_fraction)

        loss = his_penalty * self.penalty_weight * ph_sensitivity

        return loss / batch_size


class MultiStateDesignLoss(nn.Module):
    """
    Multi-state design loss for proteins that need to bind multiple targets
    or exist in multiple conformations.

    This loss ensures that the designed binder can adopt multiple states
    while maintaining structural integrity.

    Args:
        num_states (int): Number of states to design for
        state_weight (List[float]): Relative importance of each state
        consistency_weight (float): Weight for maintaining sequence consistency
    """

    def __init__(
        self,
        num_states: int = 2,
        state_weights: Optional[List[float]] = None,
        consistency_weight: float = 0.5
    ):
        super().__init__()
        self.num_states = num_states
        self.state_weights = state_weights or [1.0] * num_states
        self.consistency_weight = consistency_weight

        assert len(self.state_weights) == num_states

    def forward(
        self,
        predictions: List[Dict[str, torch.Tensor]],
        targets: List[Dict[str, torch.Tensor]]
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Calculate multi-state design loss.

        Args:
            predictions: List of predictions for each state
            targets: List of target structures for each state

        Returns:
            loss: Combined loss across all states
            metrics: Dictionary of per-state metrics
        """
        assert len(predictions) == self.num_states
        assert len(targets) == self.num_states

        total_loss = 0.0
        metrics = {}

        # Calculate loss for each state
        for i, (pred, target, weight) in enumerate(
            zip(predictions, targets, self.state_weights)
        ):
            state_loss = self._calculate_state_loss(pred, target)
            total_loss += state_loss * weight
            metrics[f'state_{i}_loss'] = state_loss.item()

        # Add sequence consistency penalty
        # Penalize different sequences across states (they should be the same)
        if self.consistency_weight > 0:
            consistency_loss = self._calculate_consistency_loss(predictions)
            total_loss += consistency_loss * self.consistency_weight
            metrics['consistency_loss'] = consistency_loss.item()

        return total_loss, metrics

    def _calculate_state_loss(
        self,
        pred: Dict[str, torch.Tensor],
        target: Dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Calculate loss for a single state."""
        # Structure loss (RMSD-based)
        pred_coords = pred['structure']
        target_coords = target['structure']
        rmsd = torch.sqrt(
            torch.mean((pred_coords - target_coords) ** 2)
        )

        # Confidence loss (penalize low pLDDT)
        if 'plddt' in pred:
            confidence_loss = torch.mean(100.0 - pred['plddt'])
        else:
            confidence_loss = 0.0

        return rmsd + 0.1 * confidence_loss

    def _calculate_consistency_loss(
        self,
        predictions: List[Dict[str, torch.Tensor]]
    ) -> torch.Tensor:
        """Ensure sequence is consistent across states."""
        sequences = [pred['sequence'] for pred in predictions]

        # Calculate pairwise sequence differences
        consistency_loss = 0.0
        num_pairs = 0

        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                diff = torch.sum((sequences[i] - sequences[j]) ** 2)
                consistency_loss += diff
                num_pairs += 1

        return consistency_loss / max(num_pairs, 1)


class InterfaceEnergyLoss(nn.Module):
    """
    Loss function for optimizing protein-protein interface energy.

    Encourages formation of favorable contacts (hydrogen bonds, hydrophobic
    packing) while penalizing unfavorable interactions.
    """

    def __init__(
        self,
        hbond_weight: float = 1.0,
        hydrophobic_weight: float = 0.8,
        electrostatic_weight: float = 1.2,
        clash_penalty: float = 10.0
    ):
        super().__init__()
        self.hbond_weight = hbond_weight
        self.hydrophobic_weight = hydrophobic_weight
        self.electrostatic_weight = electrostatic_weight
        self.clash_penalty = clash_penalty

        # Define amino acid properties
        self.hydrophobic_aa = [0, 6, 9, 11, 13, 18, 19]  # A, F, I, L, M, V, W
        self.charged_positive = [1, 10]  # R, K
        self.charged_negative = [3, 4]  # D, E

    def forward(
        self,
        sequence: torch.Tensor,
        structure: torch.Tensor,
        interface_mask: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Calculate interface energy loss.

        Args:
            sequence: One-hot encoded sequence (B, L, 20)
            structure: Structure coordinates (B, L, N_atoms, 3)
            interface_mask: Interface residue mask (B, L)

        Returns:
            loss: Interface energy loss
            metrics: Breakdown of energy components
        """
        # Extract interface residues
        interface_seq = sequence * interface_mask.unsqueeze(-1)
        interface_struct = structure * interface_mask.unsqueeze(-1).unsqueeze(-1)

        # Calculate energy components
        hbond_energy = self._calculate_hbond_energy(interface_seq, interface_struct)
        hydrophobic_energy = self._calculate_hydrophobic_energy(interface_seq, interface_struct)
        electrostatic_energy = self._calculate_electrostatic_energy(interface_seq, interface_struct)
        clash_energy = self._calculate_clash_penalty(interface_struct)

        # Combine energies (negative is favorable, positive is unfavorable)
        total_energy = (
            -self.hbond_weight * hbond_energy +
            -self.hydrophobic_weight * hydrophobic_energy +
            -self.electrostatic_weight * electrostatic_energy +
            self.clash_penalty * clash_energy
        )

        metrics = {
            'hbond_energy': hbond_energy.item(),
            'hydrophobic_energy': hydrophobic_energy.item(),
            'electrostatic_energy': electrostatic_energy.item(),
            'clash_energy': clash_energy.item()
        }

        return total_energy, metrics

    def _calculate_hbond_energy(
        self,
        sequence: torch.Tensor,
        structure: torch.Tensor
    ) -> torch.Tensor:
        """Estimate hydrogen bonding potential."""
        # Simplified H-bond potential based on distance and orientation
        # In practice, this would use proper H-bond geometry
        hbond_donors = [2, 5, 7, 8, 10, 15, 17, 19]  # N, Q, H, K, S, T, W, Y
        hbond_acceptors = [3, 4, 2, 5]  # D, E, N, Q

        # Placeholder: actual implementation would calculate distances
        # between potential H-bond donors and acceptors
        return torch.tensor(0.0, device=sequence.device)

    def _calculate_hydrophobic_energy(
        self,
        sequence: torch.Tensor,
        structure: torch.Tensor
    ) -> torch.Tensor:
        """Calculate hydrophobic packing energy."""
        # Favorable energy from hydrophobic residues in contact
        # Placeholder for actual implementation
        return torch.tensor(0.0, device=sequence.device)

    def _calculate_electrostatic_energy(
        self,
        sequence: torch.Tensor,
        structure: torch.Tensor
    ) -> torch.Tensor:
        """Calculate electrostatic interactions."""
        # Favorable for opposite charges, unfavorable for like charges
        # Placeholder for actual implementation
        return torch.tensor(0.0, device=sequence.device)

    def _calculate_clash_penalty(
        self,
        structure: torch.Tensor
    ) -> torch.Tensor:
        """Penalize steric clashes."""
        # Strong penalty for atoms too close together
        # Placeholder for actual implementation
        return torch.tensor(0.0, device=sequence.device)


class CombinedProteinDesignLoss(nn.Module):
    """
    Combined loss function integrating all custom losses for protein design.

    This is the main loss function that should be used to replace or augment
    the default AlphaFold2 loss in the ProteinDJ pipeline.
    """

    def __init__(
        self,
        use_ph_sensitive: bool = True,
        use_multistate: bool = False,
        use_interface_energy: bool = True,
        ph_value: float = 7.0,
        num_states: int = 1
    ):
        super().__init__()

        self.use_ph_sensitive = use_ph_sensitive
        self.use_multistate = use_multistate
        self.use_interface_energy = use_interface_energy

        if use_ph_sensitive:
            self.ph_loss = pHSensitiveHistidineLoss(ph_value=ph_value)

        if use_multistate:
            self.multistate_loss = MultiStateDesignLoss(num_states=num_states)

        if use_interface_energy:
            self.interface_loss = InterfaceEnergyLoss()

    def forward(
        self,
        predictions: Dict[str, torch.Tensor],
        targets: Optional[Dict[str, torch.Tensor]] = None,
        **kwargs
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Calculate combined loss.

        Args:
            predictions: Model predictions
            targets: Target values (optional)
            **kwargs: Additional arguments for specific losses

        Returns:
            total_loss: Combined loss value
            metrics: Dictionary of individual loss components
        """
        total_loss = 0.0
        metrics = {}

        # pH-sensitive histidine loss
        if self.use_ph_sensitive:
            ph_loss = self.ph_loss(
                predictions['sequence'],
                predictions['structure'],
                interface_mask=kwargs.get('interface_mask'),
                sasa=kwargs.get('sasa')
            )
            total_loss += ph_loss
            metrics['ph_histidine_loss'] = ph_loss.item()

        # Interface energy loss
        if self.use_interface_energy and 'interface_mask' in kwargs:
            interface_loss, interface_metrics = self.interface_loss(
                predictions['sequence'],
                predictions['structure'],
                kwargs['interface_mask']
            )
            total_loss += interface_loss
            metrics.update(interface_metrics)

        # Multi-state loss (if applicable)
        if self.use_multistate and 'state_predictions' in kwargs:
            multistate_loss, multistate_metrics = self.multistate_loss(
                kwargs['state_predictions'],
                kwargs['state_targets']
            )
            total_loss += multistate_loss
            metrics.update(multistate_metrics)

        return total_loss, metrics


# Utility functions for integration with ProteinDJ

def create_custom_loss(config: Dict) -> nn.Module:
    """
    Factory function to create custom loss based on configuration.

    Args:
        config: Dictionary with loss configuration

    Returns:
        loss_fn: Initialized loss function
    """
    return CombinedProteinDesignLoss(
        use_ph_sensitive=config.get('use_ph_sensitive', True),
        use_multistate=config.get('use_multistate', False),
        use_interface_energy=config.get('use_interface_energy', True),
        ph_value=config.get('ph_value', 7.0),
        num_states=config.get('num_states', 1)
    )


def integrate_with_af2_loss(
    af2_loss: torch.Tensor,
    custom_loss: torch.Tensor,
    alpha: float = 0.5
) -> torch.Tensor:
    """
    Combine custom loss with AlphaFold2's default loss.

    Args:
        af2_loss: AlphaFold2 default loss
        custom_loss: Custom domain-specific loss
        alpha: Weight for custom loss (0-1)

    Returns:
        combined_loss: Weighted combination
    """
    return (1 - alpha) * af2_loss + alpha * custom_loss


if __name__ == "__main__":
    # Example usage and testing
    print("Custom Loss Functions for ProteinDJ")
    print("=" * 50)

    # Test pH-sensitive loss
    batch_size, seq_len = 2, 100
    sequence = torch.randn(batch_size, seq_len, 20)
    structure = torch.randn(batch_size, seq_len, 3)
    interface_mask = torch.randint(0, 2, (batch_size, seq_len)).float()

    ph_loss_fn = pHSensitiveHistidineLoss(ph_value=7.0)
    loss = ph_loss_fn(sequence, structure, interface_mask)
    print(f"pH-sensitive Histidine Loss: {loss.item():.4f}")

    # Test combined loss
    combined_loss_fn = CombinedProteinDesignLoss(
        use_ph_sensitive=True,
        use_interface_energy=True
    )

    predictions = {
        'sequence': sequence,
        'structure': structure
    }

    total_loss, metrics = combined_loss_fn(
        predictions,
        interface_mask=interface_mask
    )

    print(f"\nCombined Loss: {total_loss.item():.4f}")
    print("\nMetrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
