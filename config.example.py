import tomllib
from pathlib import Path

toml_file = Path("pyproject.toml")

with open(toml_file, "rb") as f:
    data = tomllib.load(f)

project_config = data.get("tool", {}).get("market-hub-puller", {})

MAX_WORKERS: int = project_config.get("max_workers", 160)
ERROR_LIMIT_DEFAULT: str = project_config.get("error_limit_default", "100")
ERR_MIN_THRESHOLD: int = project_config.get("error_min_threshold", 10)
ERROR_TIMER_BUFFER_SECONDS: int = project_config.get("error_timer_buffer_seconds", 1)
CHUNK_LENGTH: int = project_config.get("chunk_length", 30000)
ID_SEGMENT_CHUNK: int = project_config.get("id_segment_chunk", 1000)
MIN_VALUE_OF_ITEM_OF_INTEREST: int = project_config.get(
    "min_value_of_item_of_interest", 70000000
)
LOWEST_MARGIN: float = project_config.get("lowest_margin", 0.2)
DATA_DIR: str = project_config.get("data_dir", "./market_data")
INCLUDE_HISTORY: bool = project_config.get("include_history", True)
PROCESS_DATA: bool = project_config.get("process_data", True)
SAVE_PROCESSED_DATA: bool = project_config.get("save_processed_data", True)
SAVE_SOURCE_DATA: bool = project_config.get("save_source_data", True)
PRINT_INFORMATIONAL_ERR_LIMITS: bool = False

region_hubs: dict[str, list[str]] = {
    "Jita": ["10000002", "60003760", "JitaMarketWhore"],
    "Amarr": ["10000043", "60008494", "RensMarketWhore"],
    "Dodixie": ["10000032", "60011866", "DodixeMarketWhore"],
    "Rens": ["10000030", "60004588", "HekMarketWhore"],
    "Hek": ["10000042", "60005686", "AmarrMarketWhore"],
    "Venal": [
        "10000015",
        "60012577",
        "D43dun",
    ],
}

characters = {
    "D43dun": "334156259",
    "JitaMarketWhore": "2115559643",
    "RensMarketWhore": "2115563560",
    "DodixeMarketWhore": "2115559664",
    "HekMarketWhore": "2115563507",
    "AmarrMarketWhore": "2118375567",
}

version = data["project"]["version"]
email = "user@example.com"
github_repo = "username/repo_name"
toon_name = "character_name"
discord_name = "discord_user"
user_agent: dict[str, str] = {
    "User-Agent": f"market-hub-puller/{version} ({email}; "
    f"+https://github.com/{github_repo}; discord:{discord_name}; eve:{toon_name})"
}
