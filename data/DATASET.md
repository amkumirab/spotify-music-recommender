# Dataset

The full merged catalog contains **114,206 unique track IDs**. It combines the
original audio catalog with a real chart snapshot containing releases through
2025. It is an offline snapshot, not a live view of Spotify or a complete 2026 catalog.

## Base audio catalog

**Spotify Tracks Dataset | Audio Features** by Sai Chaitanya Reddy was
downloaded from Kaggle on 2026-08-07.

- Source: https://www.kaggle.com/datasets/saichaitanyareddyai/spotify-tracks-dataset-audio-features
- Kaggle slug: `saichaitanyareddyai/spotify-tracks-dataset-audio-features`
- License: CC0 / Public Domain (as stated on the Kaggle dataset page)
- Size: approximately 114,000 tracks, 20 columns, and 114 genres

The original 114,000 rows become 89,740 unique track IDs after cleaning.

## Chart expansion

- Source: [Top Spotify Songs in 73 Countries](https://www.kaggle.com/datasets/asaniczka/top-spotify-songs-in-73-countries-daily-updated)
- Creator: **Asaniczka**
- Pinned Kaggle version: **608**, source last updated 2025-06-11
- Last observation in the downloaded CSV: **2025-06-11**
- License: [ODC Attribution License (ODC-By)](https://opendatacommons.org/licenses/by/1-0/)
- Archive SHA-256: `e048c4726c7ffb0c4e50827b459b760e98561f07202d6efb586f69fc962902ef`
- Unique chart tracks with complete audio features: **24,975**
- Net new track IDs added to the original catalog: **24,466**

The update script reads the 498 MB CSV in chunks. It keeps each track's newest
observation with complete audio features, retains known base genres, and labels
unknown genres `unclassified`. Missing audio features are excluded rather than
invented. Release years describe the observed album version, which can differ
from a song's original release. Duplicate recordings can have multiple Spotify IDs.

The merged catalog and repository sample are derived databases containing chart
data attributed to Asaniczka under ODC-By; the MIT code license does not replace
dataset licensing. Keep this attribution when sharing the sample or derived data.

## Reproduce

```bash
python scripts/download_data.py
python scripts/update_catalog.py
```

The second command verifies the pinned archive checksum and generates
`data/raw/spotify_catalog.csv`, a deterministic 2,780-track demo sample and
[`catalog_manifest.json`](catalog_manifest.json). Full datasets and archives
stay gitignored. The app prefers the merged catalog, then the original base,
then the sample. It invalidates the model cache when the selected CSV changes.
