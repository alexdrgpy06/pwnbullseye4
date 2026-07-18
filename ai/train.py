#!/usr/bin/env python3
"""
PwnBullseye4 AI Model Training and Export Script
Trains A2C model using stable-baselines3 and exports to ONNX for edge inference
"""

import os
import sys
import logging
import argparse
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
from stable_baselines3 import A2C
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_checker import check_env

# Try to import ONNX export
try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print("ONNX not available - install with: pip install onnx onnxruntime")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PwnagotchiEnv(gym.Env):
    """
    Gymnasium environment for pwnagotchi training
    Mimics the observation/action space from the original pwnagotchi
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__()
        
        # Observation space: 10 features from original pwnagotchi
        # [channel, aps_count, stas_count, rssi_avg, epoch, handshakes, 
        #  peer_count, uptime_norm, last_reward, deauth_count]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )
        
        # Action space: 14 actions from original (channel hop, deauth, associate, etc.)
        self.action_space = spaces.Discrete(14)
        
        # Action mapping
        self.actions = {
            0: "hop_channel_1",
            1: "hop_channel_6", 
            2: "hop_channel_11",
            3: "deauth_strongest",
            4: "associate_strongest",
            5: "deauth_random",
            6: "associate_random",
            7: "stay_channel",
            8: "scan_all",
            9: "focus_ap",
            10: "focus_client",
            11: "wait",
            12: "reboot",
            13: "shutdown"
        }
        
        # Episode tracking
        self.current_step = 0
        self.max_steps = 50  # epochs_per_episode
        self.episode_reward = 0
        self.last_observation = None
        
        # Simulated state
        self.aps = []
        self.stations = []
        self.channel = 1
        self.handshakes = 0
        self.deauths = 0
        self.associations = 0
        self.epoch = 0
        self.uptime = 0
        
        logger.info("PwnagotchiEnv initialized")
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.episode_reward = 0
        self.aps = self._generate_random_aps()
        self.stations = self._generate_random_stations()
        self.channel = 1
        self.handshakes = 0
        self.deauths = 0
        self.associations = 0
        self.epoch += 1
        self.uptime += 1
        
        obs = self._get_observation()
        self.last_observation = obs
        return obs, {}
        
    def step(self, action: int):
        self.current_step += 1
        reward = 0.0
        terminated = False
        truncated = False
        
        # Execute action
        reward += self._execute_action(action)
        
        # Environment dynamics
        self._update_environment()
        
        # Calculate reward
        reward += self._calculate_reward()
        
        # Episode termination
        if self.current_step >= self.max_steps:
            truncated = True
            
        # Large reward for handshake
        if self.handshakes > 0:
            reward += 10.0
            self.handshakes = 0  # Reset for next capture
            
        self.episode_reward += reward
        
        obs = self._get_observation()
        self.last_observation = obs
        
        return obs, reward, terminated, truncated, {}
        
    def _execute_action(self, action: int) -> float:
        """Execute action and return immediate reward"""
        reward = 0.0
        action_name = self.actions.get(action, "unknown")
        
        if action in [0, 1, 2]:  # Channel hop
            self.channel = [1, 6, 11][action]
            reward += 0.1  # Small reward for exploration
            
        elif action == 3:  # Deauth strongest
            if self.stations:
                self.deauths += 1
                reward += 0.5
                
        elif action == 4:  # Associate strongest
            if self.aps:
                self.associations += 1
                reward += 0.3
                
        elif action == 5:  # Deauth random
            if self.stations:
                self.deauths += 1
                reward += 0.2
                
        elif action == 6:  # Associate random
            if self.aps:
                self.associations += 1
                reward += 0.1
                
        elif action == 7:  # Stay on channel
            reward += 0.05
            
        elif action == 8:  # Scan all
            reward += 0.2
            
        elif action == 9:  # Focus AP
            reward += 0.1
            
        elif action == 10:  # Focus client
            reward += 0.1
            
        elif action == 11:  # Wait
            reward += 0.01
            
        elif action in [12, 13]:  # Reboot/Shutdown - penalize
            reward -= 5.0
            
        return reward
        
    def _update_environment(self):
        """Simulate environment changes"""
        # Randomly add/remove APs and stations
        if np.random.random() < 0.1:
            self.aps = self._generate_random_aps()
        if np.random.random() < 0.15:
            self.stations = self._generate_random_stations()
            
        # Simulate handshake capture (rare)
        if self.deauths > 0 and np.random.random() < 0.05:
            self.handshakes += 1
            self.deauths = 0
            
    def _calculate_reward(self) -> float:
        """Calculate reward based on state"""
        reward = 0.0
        
        # Reward for having APs in view
        reward += len(self.aps) * 0.1
        
        # Reward for stations (potential targets)
        reward += len(self.stations) * 0.05
        
        # Small penalty for time passing without progress
        reward -= 0.01
        
        return reward
        
    def _get_observation(self) -> np.ndarray:
        """Create observation vector"""
        # Normalize values
        channel_norm = self.channel / 11.0
        aps_count = min(len(self.aps), 50) / 50.0
        stas_count = min(len(self.stations), 100) / 100.0
        rssi_avg = -50.0  # Placeholder
        rssi_norm = (rssi_avg + 100) / 100.0  # Normalize -100 to 0
        epoch_norm = min(self.epoch, 1000) / 1000.0
        handshakes_norm = min(self.handshakes, 10) / 10.0
        peer_count = 0  # Placeholder
        uptime_norm = min(self.uptime, 3600) / 3600.0
        last_reward = self.episode_reward / 100.0 if self.episode_reward else 0
        deauth_norm = min(self.deauths, 20) / 20.0
        
        obs = np.array([
            channel_norm,
            aps_count,
            stas_count,
            rssi_norm,
            epoch_norm,
            handshakes_norm,
            peer_count,
            uptime_norm,
            last_reward,
            deauth_norm
        ], dtype=np.float32)
        
        return obs
        
    def _generate_random_aps(self):
        """Generate random APs for simulation"""
        num_aps = np.random.randint(0, 20)
        aps = []
        for i in range(num_aps):
            aps.append({
                'mac': f'{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}',
                'channel': np.random.choice([1, 6, 11]),
                'rssi': np.random.randint(-90, -30),
                'encryption': 'WPA2',
                'hostname': f'AP_{i}'
            })
        return aps
        
    def _generate_random_stations(self):
        """Generate random stations for simulation"""
        num_stas = np.random.randint(0, 30)
        stations = []
        for i in range(num_stas):
            stations.append({
                'mac': f'{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}:{np.random.randint(0,256):02x}',
                'rssi': np.random.randint(-90, -30),
                'vendor': 'Unknown'
            })
        return stations
        
    def render(self, mode='human'):
        print(f"Epoch: {self.epoch}, Step: {self.current_step}, Channel: {self.channel}")
        print(f"APs: {len(self.aps)}, Stations: {len(self.stations)}")
        print(f"Handshakes: {self.handshakes}, Reward: {self.episode_reward:.2f}")


class TrainingCallback(BaseCallback):
    """Callback for logging training progress"""
    
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        
    def _on_step(self) -> bool:
        # Log every 1000 steps
        if self.n_calls % 1000 == 0:
            logger.info(f"Training step: {self.n_calls}")
        return True
        
    def _on_rollout_end(self) -> None:
        # Called at end of each rollout (episode)
        pass


def create_env(config=None):
    """Factory function for creating vectorized environment"""
    def _init():
        env = PwnagotchiEnv(config)
        return env
    return DummyVecEnv([_init])


def train_model(config: Dict[str, Any], total_timesteps: int = 100000, 
                model_path: str = "models/brain.zip"):
    """Train A2C model"""
    
    logger.info("Creating environment...")
    env = create_env(config)
    
    # Verify environment
    check_env(env.envs[0])
    logger.info("Environment check passed")
    
    # Model configuration
    policy_kwargs = dict(
        net_arch=[64, 64],  # Small network for edge deployment
        lstm_hidden_size=32,
        enable_critic_lstm=True
    )
    
    # A2C hyperparameters (matching pwnagotchi defaults)
    a2c_params = config.get('ai', {}).get('params', {
        'gamma': 0.99,
        'n_steps': 5,
        'vf_coef': 0.25,
        'ent_coef': 0.01,
        'max_grad_norm': 0.5,
        'learning_rate': 0.001,
        'verbose': 1
    })
    
    logger.info("Creating A2C model...")
    model = A2C(
        "MlpLstmPolicy",
        env,
        policy_kwargs=policy_kwargs,
        device="cpu",  # Force CPU for compatibility
        **a2c_params
    )
    
    logger.info(f"Training for {total_timesteps} timesteps...")
    callback = TrainingCallback()
    model.learn(total_timesteps=total_timesteps, callback=callback)
    
    # Save model
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save(model_path)
    logger.info(f"Model saved to {model_path}")
    
    return model


def export_to_onnx(model_path: str, onnx_path: str, dummy_input_shape: tuple = (1, 10)):
    """Export trained model to ONNX format"""
    
    if not ONNX_AVAILABLE:
        logger.error("ONNX not available - install onnx and onnxruntime")
        return False
        
    logger.info(f"Loading model from {model_path}...")
    model = A2C.load(model_path, device="cpu")
    
    # Create dummy input
    dummy_input = torch.randn(dummy_input_shape, dtype=torch.float32)
    
    # Export policy network to ONNX
    logger.info(f"Exporting to ONNX: {onnx_path}")
    
    try:
        # Export the policy (actor) network
        torch.onnx.export(
            model.policy,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['action_logits', 'value'],  # Export action logits
            dynamic_axes={
                'input': {0: 'batch_size'},
                'action_logits': {0: 'batch_size'},
                'value': {0: 'batch_size'}
            }
        )
        
        logger.info("ONNX export successful")
        
        # Verify the model
        verify_onnx_model(onnx_path, dummy_input)
        
        return True
        
    except Exception as e:
        logger.exception(f"ONNX export failed: {e}")
        return False


def verify_onnx_model(onnx_path: str, dummy_input: torch.Tensor):
    """Verify ONNX model loads and runs correctly"""
    
    logger.info("Verifying ONNX model...")
    
    # Load with onnxruntime
    sess = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
    
    # Run inference
    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: dummy_input.numpy()})
    
    logger.info(f"ONNX model verified:")
    logger.info(f"  Input: {input_name}, shape: {dummy_input.shape}")
    logger.info(f"  Outputs: {[o.shape for o in outputs]}")
    logger.info(f"  Output names: {[o.name for o in sess.get_outputs()]}")
    
    return True


def quantize_onnx_model(onnx_path: str, quantized_path: str):
    """Quantize ONNX model to INT8 for faster inference on Pi Zero"""
    
    if not ONNX_AVAILABLE:
        logger.error("ONNX not available")
        return False
        
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        logger.info(f"Quantizing model to INT8: {quantized_path}")
        
        quantize_dynamic(
            onnx_path,
            quantized_path,
            weight_type=QuantType.QInt8,
            optimize_model=True
        )
        
        logger.info("Quantization complete")
        
        # Verify quantized model
        sess = ort.InferenceSession(quantized_path, providers=['CPUExecutionProvider'])
        logger.info(f"Quantized model verified: {sess.get_inputs()[0].name}")
        
        return True
        
    except ImportError:
        logger.warning("onnxruntime.quantization not available, skipping quantization")
        return False
    except Exception as e:
        logger.exception(f"Quantization failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Train and export PwnBullseye4 AI model")
    parser.add_argument("--train", action="store_true", help="Train new model")
    parser.add_argument("--export", action="store_true", help="Export to ONNX")
    parser.add_argument("--quantize", action="store_true", help="Quantize to INT8")
    parser.add_argument("--timesteps", type=int, default=100000, help="Training timesteps")
    parser.add_argument("--model-path", default="models/brain.zip", help="Model path")
    parser.add_argument("--onnx-path", default="models/brain.onnx", help="ONNX path")
    parser.add_argument("--quantized-path", default="models/brain_int8.onnx", help="Quantized path")
    
    args = parser.parse_args()
    
    # Default config matching pwnagotchi
    config = {
        'ai': {
            'enabled': True,
            'path': args.model_path,
            'epochs_per_episode': 50,
            'params': {
                'gamma': 0.99,
                'n_steps': 5,
                'vf_coef': 0.25,
                'ent_coef': 0.01,
                'max_grad_norm': 0.5,
                'learning_rate': 0.001,
                'verbose': 1
            }
        }
    }
    
    if args.train:
        logger.info("Starting training...")
        model = train_model(config, args.timesteps, args.model_path)
        
    if args.export:
        if not os.path.exists(args.model_path):
            logger.error(f"Model not found: {args.model_path}")
            return 1
        logger.info("Exporting to ONNX...")
        success = export_to_onnx(args.model_path, args.onnx_path)
        if not success:
            return 1
            
    if args.quantize:
        if not os.path.exists(args.onnx_path):
            logger.error(f"ONNX model not found: {args.onnx_path}")
            return 1
        logger.info("Quantizing to INT8...")
        success = quantize_onnx_model(args.onnx_path, args.quantized_path)
        if not success:
            return 1
            
    if not any([args.train, args.export, args.quantize]):
        parser.print_help()
        return 1
        
    logger.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())