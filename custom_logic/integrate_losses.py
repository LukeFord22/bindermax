#!/usr/bin/env python3
"""
Loss Function Integration Module for ProteinDJ
Purpose: Integrate custom loss functions into the AlphaFold2 pipeline

This script provides hooks and monkey-patching capabilities to inject
custom loss functions into the ProteinDJ/AlphaFold2 execution path.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import importlib.util


class LossIntegrator:
    """
    Manages integration of custom loss functions into ProteinDJ pipeline.
    """

    def __init__(self, custom_loss_path: Optional[str] = None):
        """
        Initialize the loss integrator.

        Args:
            custom_loss_path: Path to custom loss.py module
        """
        self.custom_loss_path = custom_loss_path or self._find_custom_loss()
        self.custom_loss_module = None
        self.original_loss_fn = None

    def _find_custom_loss(self) -> Optional[str]:
        """Attempt to locate custom loss.py in standard locations."""
        search_paths = [
            "/workspace/custom_logic/loss.py",
            "/workspace/custom_losses/loss.py",
            os.path.join(os.getcwd(), "custom_logic", "loss.py"),
            os.path.join(os.path.dirname(__file__), "loss.py")
        ]

        for path in search_paths:
            if os.path.exists(path):
                print(f"[LossIntegrator] Found custom loss at: {path}")
                return path

        print("[LossIntegrator] Warning: Custom loss.py not found")
        return None

    def load_custom_loss(self) -> bool:
        """
        Dynamically load the custom loss module.

        Returns:
            success: True if loaded successfully
        """
        if not self.custom_loss_path or not os.path.exists(self.custom_loss_path):
            print("[LossIntegrator] Cannot load custom loss - file not found")
            return False

        try:
            spec = importlib.util.spec_from_file_location(
                "custom_loss",
                self.custom_loss_path
            )
            self.custom_loss_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.custom_loss_module)

            print("[LossIntegrator] Successfully loaded custom loss module")
            return True

        except Exception as e:
            print(f"[LossIntegrator] Error loading custom loss: {e}")
            return False

    def create_custom_loss_fn(self, config: Optional[Dict] = None):
        """
        Create custom loss function from loaded module.

        Args:
            config: Configuration dictionary for loss function

        Returns:
            loss_fn: Custom loss function instance
        """
        if not self.custom_loss_module:
            if not self.load_custom_loss():
                return None

        config = config or {
            'use_ph_sensitive': True,
            'use_interface_energy': True,
            'ph_value': 7.0
        }

        try:
            return self.custom_loss_module.create_custom_loss(config)
        except Exception as e:
            print(f"[LossIntegrator] Error creating loss function: {e}")
            return None

    def patch_af2_loss(self, config: Optional[Dict] = None) -> bool:
        """
        Monkey-patch AlphaFold2 loss function to include custom losses.

        This is the main integration point that modifies the AF2 pipeline.

        Args:
            config: Loss configuration

        Returns:
            success: True if patching successful
        """
        print("[LossIntegrator] Attempting to patch AlphaFold2 loss function...")

        custom_loss_fn = self.create_custom_loss_fn(config)
        if custom_loss_fn is None:
            print("[LossIntegrator] Failed to create custom loss - aborting patch")
            return False

        try:
            # Import AlphaFold2 modules (adjust paths based on actual structure)
            # This is a template - actual implementation depends on AF2 structure
            import alphafold
            from alphafold.model import model

            # Store original loss function
            if hasattr(model, 'compute_loss'):
                self.original_loss_fn = model.compute_loss

                # Create wrapper that combines original + custom loss
                def combined_loss_wrapper(*args, **kwargs):
                    # Get original loss
                    orig_loss = self.original_loss_fn(*args, **kwargs)

                    # Calculate custom loss
                    try:
                        custom_loss, metrics = custom_loss_fn(
                            predictions=kwargs.get('predictions', {}),
                            interface_mask=kwargs.get('interface_mask')
                        )

                        # Combine losses
                        alpha = config.get('custom_loss_weight', 0.3)
                        combined = (1 - alpha) * orig_loss + alpha * custom_loss

                        # Log metrics
                        if hasattr(kwargs, 'metrics_dict'):
                            kwargs['metrics_dict'].update(metrics)

                        return combined

                    except Exception as e:
                        print(f"[LossIntegrator] Error in custom loss: {e}")
                        return orig_loss  # Fall back to original

                # Apply the patch
                model.compute_loss = combined_loss_wrapper
                print("[LossIntegrator] Successfully patched AlphaFold2 loss function")
                return True

            else:
                print("[LossIntegrator] Warning: Could not find AF2 loss function to patch")
                return False

        except ImportError as e:
            print(f"[LossIntegrator] Could not import AlphaFold2 modules: {e}")
            print("[LossIntegrator] This is expected if AF2 is not in the Python path")
            return False

        except Exception as e:
            print(f"[LossIntegrator] Unexpected error during patching: {e}")
            return False

    def restore_original_loss(self):
        """Restore the original AlphaFold2 loss function."""
        if self.original_loss_fn:
            try:
                from alphafold.model import model
                model.compute_loss = self.original_loss_fn
                print("[LossIntegrator] Restored original AF2 loss function")
            except Exception as e:
                print(f"[LossIntegrator] Error restoring original loss: {e}")


def setup_proteindj_custom_losses(config_file: Optional[str] = None) -> bool:
    """
    Main setup function to integrate custom losses into ProteinDJ.

    This should be called at the start of the ProteinDJ pipeline.

    Args:
        config_file: Path to YAML/JSON config with loss parameters

    Returns:
        success: True if setup successful
    """
    print("=" * 60)
    print("ProteinDJ Custom Loss Integration")
    print("=" * 60)

    # Load configuration
    config = {}
    if config_file and os.path.exists(config_file):
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)

    # Initialize integrator
    integrator = LossIntegrator()

    # Load and patch
    success = integrator.patch_af2_loss(config)

    if success:
        print("[SUCCESS] Custom losses integrated successfully")
        print(f"Configuration: {config}")
    else:
        print("[WARNING] Running with default AlphaFold2 losses")

    print("=" * 60)
    return success


# Command-line interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Integrate custom loss functions into ProteinDJ"
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to loss configuration file (JSON)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run test mode without patching'
    )

    args = parser.parse_args()

    if args.test:
        print("Running in TEST mode")
        integrator = LossIntegrator()
        if integrator.load_custom_loss():
            print("✓ Custom loss module loaded successfully")

            # Test loss creation
            loss_fn = integrator.create_custom_loss_fn()
            if loss_fn:
                print("✓ Custom loss function created successfully")
            else:
                print("✗ Failed to create loss function")
        else:
            print("✗ Failed to load custom loss module")

    else:
        setup_proteindj_custom_losses(args.config)
