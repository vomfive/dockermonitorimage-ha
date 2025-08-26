DOMAIN = "docker_monitor_image"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"

DEFAULT_UPDATE_PATH = "/update_container"
DEFAULT_SCAN_INTERVAL = 30

CONF_CONTAINERS = "containers" 

SENSOR_KEYS = [
    "cpu",
    "mem_perc",
    "mem_usage",
    "net_rx",
    "net_tx",
    "blk_read",
    "blk_write",
    "state",
]

UPDATE_STATUS_KEY = "update_status_image"