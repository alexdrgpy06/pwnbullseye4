# PwnBullseye4 WPA-Sec Configuration Guide

## What is WPA-Sec?

WPA-Sec (https://wpa-sec.stanev.org) is a community-driven project for cracking WPA/WPA2 handshakes. Users upload handshakes, and the distributed network attempts to crack them using wordlists and rules.

## Why Use WPA-Sec?

- **Free cracking** - No need for your own GPU rig
- **Community wordlists** - Benefits from massive combined wordlists
- **Automatic** - Uploads happen in background
- **Results download** - Get cracked passwords automatically

## Setup Instructions

### 1. Create Account

1. Go to https://wpa-sec.stanev.org
2. Register for a free account
3. Note your **API Key** (shown on dashboard after login)

### 2. Configure PwnBullseye4

Edit `/etc/pwnagotchi/config.toml`:

```toml
# Enable WPA-Sec plugin
main.plugins.wpa-sec.enabled = true

# Your API key from wpa-sec.stanev.org
main.plugins.wpa-sec.api_key = "YOUR_API_KEY_HERE"

# API URL (default is fine)
main.plugins.wpa-sec.api_url = "https://wpa-sec.stanev.org"

# Download cracked results automatically
main.plugins.wpa-sec.download_results = true

# Whitelist - don't upload these networks (optional)
main.plugins.wpa-sec.whitelist = [
    "YourHomeNetwork",
    "aa:bb:cc:dd:ee:ff"  # MAC prefix or full MAC
]
```

### 3. Restart Pwnagotchi

```bash
sudo systemctl restart pwnagotchi
```

## How It Works

### Upload Flow

1. Pwnagotchi captures handshake (WPA 4-way or PMKID)
2. Handshake saved to `/etc/pwnagotchi/handshakes/`
3. WPA-Sec plugin detects new handshake
4. Plugin uploads to wpa-sec.stanev.org via HTTPS
5. Server queues for cracking
6. Results available on website and auto-downloaded

### Download Flow

1. Plugin periodically checks for cracked results
2. Downloads `.potfile` entries
3. Saves to `/etc/pwnagotchi/wpa-sec-results.potfile`
4. Logs successful cracks

## Verifying It Works

### Check Logs

```bash
# Follow pwnagotchi log
sudo tail -f /var/log/pwnagotchi.log | grep -i wpa-sec

# Check plugin log
sudo journalctl -u pwnagotchi -f | grep wpa-sec
```

### Expected Log Output

```
[INFO] [plugins.wpa-sec] Uploading handshake: aa:bb:cc:dd:ee:ff -> 11:22:33:44:55:66
[INFO] [plugins.wpa-sec] Upload successful: handshake queued for cracking
[INFO] [plugins.wpa-sec] Downloading results...
[INFO] [plugins.wpa-sec] Found 3 new cracked passwords
```

### Check Results

```bash
# View cracked passwords
cat /etc/pwnagotchi/wpa-sec-results.potfile

# Format: MAC:ESSID:PASSWORD
# aa:bb:cc:dd:ee:ff:MyNetwork:password123
```

## Whitelist Configuration

Prevent uploading your own networks or sensitive environments:

```toml
main.plugins.wpa-sec.whitelist = [
    "HomeNetwork",           # By ESSID (exact match)
    "OfficeWiFi",            # Another ESSID
    "aa:bb:cc:",             # MAC prefix (first 3 octets)
    "11:22:33:44:55:66"      # Full MAC address
]
```

## Advanced Configuration

### Custom Wordlists (Server-side)

On wpa-sec website, you can:
- Add custom wordlists to your account
- Prioritize certain wordlists
- Track cracking progress per handshake

### Rate Limiting

The plugin respects server rate limits:
- Max 10 uploads per minute
- Max 100 downloads per hour
- Automatic backoff on 429 responses

### Proxy Support

If behind corporate proxy:

```toml
main.plugins.wpa-sec.proxy = "http://proxy.example.com:8080"
```

## Troubleshooting

### "Upload failed: 401 Unauthorized"
- Check API key is correct
- Regenerate key on wpa-sec website
- Ensure no extra spaces in config

### "Upload failed: 429 Too Many Requests"
- Rate limited - wait a few minutes
- Plugin auto-retries with exponential backoff

### No handshakes uploading
- Verify `main.plugins.wpa-sec.enabled = true`
- Check handshakes are being captured: `ls /etc/pwnagotchi/handshakes/`
- Verify bettercap is capturing: `sudo systemctl status bettercap`

### Results not downloading
- Enable `download_results = true`
- Check network connectivity to wpa-sec.stanev.org
- Verify API key has download permissions

## Privacy Considerations

- Handshakes contain BSSID, ESSID, and encrypted handshake data
- No plaintext passwords in uploads
- Consider whitelisting your own networks
- WPA-Sec privacy policy: https://wpa-sec.stanev.org/privacy

## Monitoring Dashboard

Access your cracking stats at:
- https://wpa-sec.stanev.org/dashboard
- Shows: Uploaded, Cracked, Pending, Failed
- Per-handshake status and history

## Integration with Web UI

PwnBullseye4 web UI (port 8080) shows:
- WPA-Sec upload status
- Recent uploads
- Cracked passwords
- Plugin configuration

Navigate to: `http://pwnbullseye4.local:8080/plugins/wpa-sec`

## API Reference

For developers, the plugin uses these endpoints:

```
POST /api/upload     - Upload handshake (.pcap/.hccapx)
GET  /api/results    - Download cracked results
GET  /api/status     - Check handshake status
```

See https://wpa-sec.stanev.org/api for full documentation.