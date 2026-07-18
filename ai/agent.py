#!/usr/bin/env python3
"""
PwnBullseye4 Modern AI Agent
Uses ONNX Runtime for fast, non-blocking inference on Pi Zero W/2W
Falls back to heuristic policy when model not ready
"""

import os
import json
import logging
import threading
import time
import random
import numpy as np
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


class HeuristicPolicy:
    """Fallback policy when AI model is not loaded - random exploration"""
    
    def __init__(self, action_space_size: int = 14):
        self.action_space_size = action_space_size
        self.logger = logging.getLogger(__name__)
        
    def predict(self, observation: np.ndarray, deterministic: bool = False) -> Tuple[int, None]:
        """Random action for exploration"""
        action = random.randint(0, self.action_space_size - 1)
        self.logger.debug(f"Heuristic policy: random action {action}")
        return action, None


class AsyncONNXAgent:
    """
    Async ONNX Runtime agent for fast inference on edge devices
    - Loads model in background thread
    - Non-blocking inference with queue
    - Falls back to heuristic policy during load
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('ai', {})
        self.model_path = self.config.get('path', '/root/brain.onnx')
        self.backend = self.config.get('inference_backend', 'onnxruntime')
        self.async_inference = self.config.get('async_inference', True)
        self.fallback_policy_name = self.config.get('fallback_policy', 'heuristic')
        
        self.logger = logging.getLogger(__name__)
        
        # Model state
        self.session = None
        self.input_name = None
        self.output_name = None
        self.model_ready = threading.Event()
        self.load_thread = None
        
        # Inference queue for async processing
        self.inference_queue = []
        self.inference_lock = threading.Lock()
        self.inference_results = {}
        self.request_counter = 0
        
        # Fallback policy
        self.fallback = HeuristicPolicy()
        
        # Stats
        self.inference_times = []
        self.total_requests = 0
        self.fallback_count = 0
        
    def start_loading(self):
        """Start loading model in background thread"""
        if self.load_thread is not None and self.load_thread.is_alive():
            self.logger.warning("Model load already in progress")
            return
            
        self.logger.info(f"Starting async model load from {self.model_path}")
        self.load_thread = threading.Thread(target=self._load_model, daemon=True, name="AI-Model-Loader")
        self.load_thread.start()
        
    def _load_model(self):
        """Load ONNX model in background"""
        try:
            if not os.path.exists(self.model_path):
                self.logger.warning(f"Model not found at {self.model_path}, will use fallback policy")
                self.model_ready.set()  # Signal ready even without model
                return
                
            # Import ONNX Runtime
            import onnxruntime as ort
            
            # Configure session options for Pi Zero
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 1  # Single thread for Pi Zero
            sess_options.inter_op_num_threads = 1
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # CPU execution provider (only option on Pi)
            providers = ['CPUExecutionProvider']
            
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=providers
            )
            
            # Get input/output names
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            
            self.logger.info(f"Model loaded successfully: input={self.input_name}, output={self.output_name}")
            self.logger.info(f"Input shape: {self.session.get_inputs()[0].shape}")
            self.logger.info(f"Output shape: {self.session.get_outputs()[0].shape}")
            
        except ImportError:
            self.logger.error("onnxruntime not installed, falling back to heuristic policy")
        except Exception as e:
            self.logger.exception(f"Failed to load model: {e}")
        finally:
            self.model_ready.set()  # Signal completion (success or failure)
            
    def predict(self, observation: np.ndarray, deterministic: bool = False) -> Tuple[int, None]:
        """
        Predict action - non-blocking if async, falls back to heuristic if model not ready
        """
        self.total_requests += 1
        
        # Check if model is ready
        if not self.model_ready.is_set():
            self.fallback_count += 1
            self.logger.debug("Model not ready, using fallback policy")
            return self.fallback.predict(observation, deterministic)
            
        # Model loaded but failed (session is None)
        if self.session is None:
            self.fallback_count += 1
            return self.fallback.predict(observation, deterministic)
            
        # Run inference
        start = time.perf_counter()
        try:
            # Ensure observation has batch dimension
            if observation.ndim == 1:
                observation = observation.reshape(1, -1)
                
            # Run inference
            outputs = self.session.run([self.output_name], {self.input_name: observation.astype(np.float32)})
            action = int(np.argmax(outputs[0]))
            
            elapsed = (time.perf_counter() - start) * 1000
            self.inference_times.append(elapsed)
            if len(self.inference_times) > 100:
                self.inference_times.pop(0)
                
            self.logger.debug(f"Inference took {elapsed:.1f}ms, action={action}")
            return action, None
            
        except Exception as e:
            self.logger.exception(f"Inference failed: {e}")
            self.fallback_count += 1
            return self.fallback.predict(observation, deterministic)
            
    def predict_async(self, observation: np.ndarray, callback, deterministic: bool = False):
        """
        Async prediction with callback - for future enhancement
        Currently runs synchronously but returns immediately if model not ready
        """
        if self.async_inference and self.model_ready.is_set() and self.session is not None:
            # Could implement thread pool here for true async
            action, _ = self.predict(observation, deterministic)
            callback(action)
        else:
            # Fallback is synchronous but fast
            action, _ = self.predict(observation, deterministic)
            callback(action)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_inference = np.mean(self.inference_times) if self.inference_times else 0
        return {
            'model_loaded': self.session is not None,
            'model_path': self.model_path,
            'total_requests': self.total_requests,
            'fallback_count': self.fallback_count,
            'fallback_rate': self.fallback_count / max(1, self.total_requests),
            'avg_inference_ms': round(avg_inference, 2),
            'min_inference_ms': round(np.min(self.inference_times), 2) if self.inference_times else 0,
            'max_inference_ms': round(np.max(self.inference_times), 2) if self.inference_times else 0,
        }
        
    def is_ready(self) -> bool:
        """Check if model is loaded and ready"""
        return self.model_ready.is_set() and self.session is not None


class PwnBullseye4Agent:
    """
    Main agent wrapper that integrates with pwnagotchi
    Provides async AI with proper fallback
    """
    
    def __init__(self, config: Dict[str, Any], epoch, view):
        self.config = config
        self.epoch = epoch
        self.view = view
        self.logger = logging.getLogger(__name__)
        
        # Initialize async ONNX agent
        self.ai_agent = AsyncONNXAgent(config)
        
        # Start loading model in background
        self.ai_agent.start_loading()
        
        # Action space from environment
        self.action_space_size = 14  # Default, will be updated by env
        
    def act(self, observation: np.ndarray) -> int:
        """Main action selection - called by environment"""
        action, _ = self.ai_agent.predict(observation)
        return action
        
    def on_epoch_start(self):
        """Called at start of each epoch"""
        stats = self.ai_agent.get_stats()
        self.logger.info(f"AI Stats: {json.dumps(stats)}")
        
        # Update view with AI status
        if self.ai_agent.is_ready():
            self.view.on_ai_ready()
        else:
            self.view.set('ai_status', 'loading...')
            
    def save_model(self, path: Optional[str] = None):
        """Save model (not applicable for ONNX, but kept for compatibility)"""
        self.logger.info("ONNX models are pre-trained and exported, not saved at runtime")
        
    def get_ai_stats(self) -> Dict[str, Any]:
        """Get AI performance statistics"""
        return self.ai_agent.get_stats()


# Compatibility wrapper for existing pwnagotchi code
class AIModelWrapper:
    """
    Wrapper that mimics stable-baselines3 A2C interface
    but uses our async ONNX agent
    """
    
    def __init__(self, config: Dict[str, Any], epoch, view):
        self.agent = PwnBullseye4Agent(config, epoch, view)
        self.env = None
        self.config = config
        
    def predict(self, observation: np.ndarray, deterministic: bool = False) -> Tuple[np.ndarray, None]:
        """SB3-compatible predict interface"""
        action = self.agent.act(observation)
        return np.array([action]), None
        
    def learn(self, total_timesteps: int, callback=None):
        """
        Training not supported on device - models are pre-trained
        This is a no-op for compatibility
        """
        self.agent.logger.info("Training not supported on device - models are pre-trained")
        if callback:
            callback()
            
    def save(self, path: str):
        """No-op save for compatibility"""
        self.agent.logger.info(f"Save requested to {path} - ONNX models are pre-exported")
        
    @property
    def env(self):
        return self._env
        
    @env.setter
    def env(self, value):
        self._env = value
        if hasattr(value, 'action_space'):
            self.agent.action_space_size = value.action_space.n


def create_agent(config: Dict[str, Any], epoch, view) -> AIModelWrapper:
    """Factory function to create the modern AI agent"""
    return AIModelWrapper(config, epoch, view)


# For backward compatibility with existing ai.load() calls
def load(config: Dict[str, Any], agent, epoch, from_disk: bool = True):
    """
    Replacement for pwnagotchi.ai.load()
    Returns our modern agent wrapper
    """
    # Create view proxy if needed
    class ViewProxy:
        def __init__(self, agent):
            self.agent = agent
            
        def on_ai_ready(self):
            if hasattr(self.agent, 'view') and self.agent.view:
                self.agent.view.on_ai_ready()
                
        def set(self, key, value):
            if hasattr(self.agent, 'view') and self.agent.view:
                self.agent.view.set(key, value)
                
    view_proxy = ViewProxy(agent)
    return create_agent(config, epoch, view_proxy)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.DEBUG)
    
    test_config = {
        'ai': {
            'enabled': True,
            'path': '/root/brain.onnx',
            'inference_backend': 'onnxruntime',
            'async_inference': True,
            'fallback_policy': 'heuristic'
        }
    }
    
    class MockEpoch:
        pass
        
    class MockView:
        def on_ai_ready(self):
            print("View: AI Ready!")
        def set(self, k, v):
            print(f"View: {k} = {v}")
            
    agent = create_agent(test_config, MockEpoch(), MockView())
    
    # Wait a bit for model load attempt
    time.sleep(1)
    
    # Test prediction
    obs = np.random.randn(10).astype(np.float32)
    action = agent.act(obs)
    print(f"Action: {action}")
    
    # Stats
    print(f"Stats: {agent.get_ai_stats()}")