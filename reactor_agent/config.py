"""
Reactor 220B operating thresholds and constants.
All domain knowledge is version-controlled here; secrets live in .env.
"""

THRESHOLDS = {
    "temp_alarm": 92.0,        # °C — triggers alarm
    "temp_interlock": 98.0,    # °C — triggers interlock TRP-12
    "ramp_rate_max": 1.5,      # °C/min — max safe ramp rate
    "agitator_min": 280,       # RPM — minimum safe agitator speed
    "delta_t_max": 15.0,       # °C — max (reactor − jacket) delta
    "feed_b_step": 5.0,        # kg/h — step change threshold for Feed B
}

# Interval between sensor readings (minutes)
SENSOR_INTERVAL_MIN = 2

# Required CSV columns
REQUIRED_COLUMNS = [
    "timestamp",
    "reactor_temp",
    "jacket_temp",
    "pressure",
    "flow_rate",
    "pH",
    "agitator_rpm",
    "feed_A_kgph",
    "feed_B_kgph",
]

# Number of RAG chunks to retrieve
RAG_TOP_K = 5

# FAISS index storage path (relative to reactor_agent/)
FAISS_INDEX_PATH = ".tmp/faiss_index"

# Chunk size for document splitting
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
