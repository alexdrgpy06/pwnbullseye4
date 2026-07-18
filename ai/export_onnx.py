#!/usr/bin/env python3
"""
Export trained PwnBullseye4 model to ONNX format for edge inference
"""

import argparse
import logging
import os
import sys

import numpy as np
import torch
import onnx
import onnxruntime as ort

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.agent import PwnagotchiEnv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_to_onnx(model_path: str, onnx_path: str, opset_version: int = 11):
    """Export stable-baselines3 A2C model to ONNX"""
    
    logger.info(f"Loading model from {model_path}...")
    
    # Load the model
    from stable_baselines3 import A2C
    
    # Create dummy env to get observation space
    env = PwnagotchiEnv()
    obs_space = env.observation_space
    
    model = A2C.load(model_path, env=env, device="cpu")
    
    # Create dummy input
    dummy_input = torch.randn(1, *obs_space.shape, dtype=torch.float32)
    
    logger.info(f"Exporting to ONNX: {onnx_path}")
    logger.info(f"Input shape: {dummy_input.shape}")
    logger.info(f"Opset version: {opset_version}")
    
    # Export the policy network
    # We export the actor (policy) network which outputs action logits
    policy = model.policy
    policy.eval()
    
    # Export using torch.onnx
    torch.onnx.export(
        policy,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['action_logits', 'value'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'action_logits': {0: 'batch_size'},
            'value': {0: 'batch_size'}
        }
    )
    
    logger.info("ONNX export completed!")
    
    # Verify the model
    verify_onnx_model(onnx_path, dummy_input)
    
    return onnx_path


def verify_onnx_model(onnx_path: str, dummy_input: torch.Tensor):
    """Verify ONNX model loads and runs correctly"""
    
    logger.info("Verifying ONNX model...")
    
    # Load with onnxruntime
    sess = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
    
    input_name = sess.get_inputs()[0].name
    output_names = [o.name for o in sess.get_outputs()]
    
    logger.info(f"Input: {input_name}")
    logger.info(f"Outputs: {output_names}")
    
    # Run inference
    outputs = sess.run(output_names, {input_name: dummy_input.numpy()})
    
    logger.info(f"Output shapes: {[o.shape for o in outputs]}")
    
    # Verify output values are reasonable
    action_logits = outputs[0]
    value = outputs[1]
    
    logger.info(f"Action logits range: [{action_logits.min():.3f}, {action_logits.max():.3f}]")
    logger.info(f"Value range: [{value.min():.3f}, {value.max():.3f}]")
    
    # Check that we get valid actions
    action = np.argmax(action_logits, axis=-1)
    logger.info(f"Predicted action: {action[0]}")
    
    # Also load with onnx package for graph validation
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    logger.info("ONNX model validation passed!")
    
    return True


def quantize_onnx_model(onnx_path: str, quantized_path: str):
    """Quantize ONNX model to INT8 for faster inference on Pi Zero"""
    
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        logger.info(f"Quantizing model to INT8: {quantized_path}")
        
        quantize_dynamic(
            onnx_path,
            quantized_path,
            weight_type=QuantType.QInt8,
            optimize_model=True
        )
        
        logger.info("Quantization completed!")
        
        # Verify quantized model
        sess = ort.InferenceSession(quantized_path, providers=['CPUExecutionProvider'])
        logger.info(f"Quantized model loaded successfully")
        logger.info(f"Inputs: {[i.name for i in sess.get_inputs()]}")
        logger.info(f"Outputs: {[o.name for o in sess.get_outputs()]}")
        
        return True
        
    except ImportError:
        logger.warning("onnxruntime.quantization not available, skipping quantization")
        logger.warning("Install with: pip install onnxruntime-tools")
        return False
    except Exception as e:
        logger.error(f"Quantization failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Export PwnBullseye4 model to ONNX")
    parser.add_argument("--model", default="models/brain.zip", help="Path to trained .zip model")
    parser.add_argument("--onnx", default="models/brain.onnx", help="Output ONNX path")
    parser.add_argument("--quantized", default="models/brain_int8.onnx", help="Output quantized ONNX path")
    parser.add_argument("--opset", type=int, default=11, help="ONNX opset version")
    parser.add_argument("--quantize", action="store_true", help="Also quantize to INT8")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing ONNX model")
    
    args = parser.parse_args()
    
    if args.verify_only:
        if not os.path.exists(args.onnx):
            logger.error(f"ONNX model not found: {args.onnx}")
            return 1
        logger.info(f"Verifying existing model: {args.onnx}")
        env = PwnagotchiEnv()
        dummy_input = torch.randn(1, *env.observation_space.shape, dtype=torch.float32)
        verify_onnx_model(args.onnx, dummy_input)
        return 0
    
    if not os.path.exists(args.model):
        logger.error(f"Model not found: {args.model}")
        logger.info("Train a model first with: python -m ai.train --train --model models/brain.zip")
        return 1
    
    # Export to ONNX
    os.makedirs(os.path.dirname(args.onnx), exist_ok=True)
    export_to_onnx(args.model, args.onnx, args.opset)
    
    # Quantize if requested
    if args.quantize:
        os.makedirs(os.path.dirname(args.quantized), exist_ok=True)
        quantize_onnx_model(args.onnx, args.quantized)
    
    logger.info("Export complete!")
    logger.info(f"  ONNX model: {args.onnx}")
    if args.quantize:
        logger.info(f"  Quantized: {args.quantized}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())